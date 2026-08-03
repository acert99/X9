"""
X9Agent

Orquestra todos os demais modulos: abre a camera quando o usuario
manda iniciar pela bandeja, roda o detector a cada frame, aplica o
filtro temporal, dispara notificacao com cooldown quando confirma
presenca, e mantem o status exibido na bandeja atualizado.

Este e o unico modulo que conhece todos os outros. Camera,
detector, filtro temporal, notificador e bandeja nao se conhecem
entre si, o que permite trocar qualquer um deles sem tocar nos
demais.

Rodar a partir da raiz do projeto:
    python src/main.py
"""

from __future__ import annotations

import logging
import logging.handlers
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from camera import CameraManager
from config import Config
from detector import PersonDetector
from notifier import NotificationService
from paths import resource_path, user_data_dir
from temporal_filter import TemporalFilter
from tray import TrayInterface


def setup_logging(config: Config, log_path: Path) -> None:
    level = getattr(logging, config.logging.level.upper(), logging.INFO)
    handlers = [logging.StreamHandler()]
    if log_path:
        handlers.append(
            logging.handlers.RotatingFileHandler(
                log_path,
                maxBytes=2_000_000,
                backupCount=3,
                encoding="utf-8",
            )
        )
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=handlers,
    )


class X9Agent:
    def __init__(self, config: Config, model_path: Path) -> None:
        self._config = config
        self._logger = logging.getLogger("x9.main")

        self._camera = CameraManager(
            index=config.camera.index,
            width=config.camera.width,
            height=config.camera.height,
            fps=config.camera.fps,
            open_retries=config.camera.open_retries,
            open_retry_delay_seconds=config.camera.open_retry_delay_seconds,
        )
        self._detector = PersonDetector(
            model_path=str(model_path),
            input_size=config.detector.input_size,
            confidence=config.detector.confidence,
            nms_threshold=config.detector.nms_threshold,
        )
        self._temporal_filter = TemporalFilter(
            window_seconds=config.detector.window_seconds,
            positive_frames_required=config.detector.positive_frames,
        )
        self._notifier = NotificationService(
            urls=config.notification.urls,
            cooldown_seconds=config.notification.cooldown_seconds,
            title=config.notification.title,
            message=config.notification.message,
        )
        self._tray = TrayInterface(
            on_start=self.start_monitoring,
            on_stop=self.stop_monitoring,
            on_exit=self.shutdown,
        )

        self._stop_event = threading.Event()
        self._monitor_thread: Optional[threading.Thread] = None
        self._alert_count = 0

    def run(self) -> None:
        self._logger.info("X9 iniciado, aguardando comando na bandeja")
        self._tray.run()

    def start_monitoring(self) -> None:
        if self._monitor_thread is not None and self._monitor_thread.is_alive():
            self._logger.info("Monitoramento ja esta em execucao")
            return

        if not self._camera.open():
            self._tray.update_status(camera_ok=False)
            self._notifier.notify("falha ao abrir a camera")
            return

        self._tray.update_status(monitoring=True, camera_ok=True, detector_ok=True)
        self._stop_event.clear()
        self._temporal_filter.reset()
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        self._logger.info("Monitoramento iniciado")

    def stop_monitoring(self) -> None:
        self._stop_event.set()
        if self._monitor_thread is not None:
            self._monitor_thread.join(timeout=5)
        self._camera.release()
        self._tray.update_status(monitoring=False)
        self._logger.info("Monitoramento parado")

    def shutdown(self) -> None:
        self.stop_monitoring()
        self._logger.info("X9 encerrado")

    def _monitor_loop(self) -> None:
        interval = 1.0 / self._config.camera.fps

        while not self._stop_event.is_set():
            loop_start = time.monotonic()
            frame = self._camera.read_frame()

            if frame is None:
                self._tray.update_status(camera_ok=False)
                time.sleep(interval)
                continue

            detected, _confidence = self._detector.detect_person(frame)
            self._temporal_filter.push(time.time(), detected)

            if self._temporal_filter.is_confirmed():
                sent = self._notifier.notify()
                if sent:
                    self._alert_count += 1
                    self._tray.update_status(
                        last_presence=datetime.now().strftime("%H:%M"),
                        alert_count=self._alert_count,
                    )
                self._temporal_filter.reset()

            elapsed = time.monotonic() - loop_start
            time.sleep(max(0.0, interval - elapsed))


def main() -> None:
    data_dir = user_data_dir()
    config_path = data_dir / "config.yaml"
    log_path = data_dir / "x9.log"

    if not config_path.exists():
        from setup_wizard import run_first_time_setup

        completed = run_first_time_setup(config_path)
        if not completed:
            return

    # Resolvido a cada execucao (nao persistido em config.yaml): em modo
    # PyInstaller onefile, o diretorio de extracao (_MEIxxxxx) e novo a
    # cada processo, entao um caminho gravado numa execucao anterior nao
    # existe mais na proxima.
    model_path = resource_path("models/yolox_nano.onnx")
    if not model_path.exists():
        raise FileNotFoundError(
            f"Modelo nao encontrado em {model_path}. "
            "Rode scripts/download_model.py antes de iniciar o agente."
        )

    config = Config.load(config_path)
    setup_logging(config, log_path)
    agent = X9Agent(config, model_path)
    agent.run()


if __name__ == "__main__":
    main()
