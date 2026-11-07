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

from camera import CameraManager, list_cameras
from config import Config, save_camera_index
from detector import PersonDetector
from face_auth import FaceAuth
from locker import lock_workstation
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
    def __init__(
        self,
        config: Config,
        model_path: Path,
        config_path: Optional[Path] = None,
        face_auth: Optional[FaceAuth] = None,
    ) -> None:
        self._config = config
        self._config_path = config_path
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
            list_cameras=list_cameras,
            on_select_camera=self.select_camera,
            current_camera=lambda: self._camera.index,
            face_enabled=face_auth is not None,
            trusted_count=lambda: self._face_auth.trusted_count if self._face_auth else 0,
            on_enroll_camera=self.enroll_from_camera,
            on_enroll_photo=self.enroll_from_photo,
            on_clear_faces=self.clear_faces,
        )
        self._face_auth = face_auth
        self._enrolling = False
        self._last_alert_trusted = False

        self._lock_screen = lock_workstation
        self._stop_event = threading.Event()
        self._monitor_thread: Optional[threading.Thread] = None
        self._alert_count = 0
        self._last_detection_at: Optional[float] = None

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
        self._last_detection_at = None
        self._last_alert_trusted = False
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

    def select_camera(self, index: int) -> None:
        """Troca a camera pela bandeja e lembra a escolha no config.yaml."""
        if index == self._camera.index:
            return
        was_monitoring = (
            self._monitor_thread is not None and self._monitor_thread.is_alive()
        )
        if was_monitoring:
            self.stop_monitoring()
        self._camera.set_index(index)
        self._config.camera.index = index
        if self._config_path is not None:
            try:
                save_camera_index(self._config_path, index)
            except (OSError, ValueError):
                self._logger.exception("Nao consegui gravar a camera escolhida")
        self._logger.info("Camera trocada para o indice %d", index)
        if was_monitoring:
            self.start_monitoring()

    # ---------- pessoa confiavel ----------

    def _is_monitoring(self) -> bool:
        return self._monitor_thread is not None and self._monitor_thread.is_alive()

    def enroll_from_camera(self) -> None:
        """Cadastro guiado: janela com a camera ao vivo pedindo poses
        variadas (de frente, lados, queixo, perto, longe). So o vetor de
        cada rosto e salvo, nunca a imagem."""
        if self._face_auth is None:
            return
        if self._is_monitoring():
            self._tray.notify("Pare o monitoramento antes de cadastrar o rosto.")
            return
        if self._enrolling:
            return
        self._enrolling = True
        try:
            from enroll_window import run_guided_enrollment

            # Camera propria com fps maior, para a previa ficar fluida.
            camera = CameraManager(
                index=self._camera.index,
                width=self._config.camera.width,
                height=self._config.camera.height,
                fps=15,
                open_retries=1,
            )
            samples = run_guided_enrollment(camera, self._face_auth)
        except Exception:
            self._logger.exception("Falha no cadastro guiado")
            self._tray.notify("Erro no cadastro de rosto, veja o x9.log.")
            return
        finally:
            self._enrolling = False

        if samples is None:
            self._tray.notify("Cadastro cancelado ou camera indisponivel. Nada foi salvo.")
            return
        added = self._face_auth.add_embeddings(samples)
        if added:
            self._tray.notify(f"Rosto cadastrado ({added} amostras).")
        else:
            self._tray.notify("Nenhuma amostra boa. Tente com mais luz.")
        self._tray.refresh()

    def enroll_from_photo(self, path: str) -> None:
        if self._face_auth is None or not path:
            return
        if self._is_monitoring():
            self._tray.notify("Pare o monitoramento antes de cadastrar o rosto.")
            return
        import cv2
        import numpy as np

        # np.fromfile + imdecode aceita caminho com acento, cv2.imread nao.
        image = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)
        if image is None:
            self._tray.notify("Nao consegui abrir essa imagem.")
            return
        added = self._face_auth.enroll([image])
        self._tray.notify(
            "Rosto cadastrado a partir da foto."
            if added
            else "A foto precisa ter exatamente um rosto bem visivel."
        )
        self._tray.refresh()

    def clear_faces(self) -> None:
        if self._face_auth is not None:
            self._face_auth.clear()
            self._tray.notify("Rostos confiaveis apagados.")
            self._tray.refresh()

    def _check_trusted(self, first_frame) -> bool:
        """Olha alguns frames: confiavel so se aparecer rosto cadastrado
        e nenhum rosto desconhecido. Sem rosto visivel conta como estranho."""
        if self._face_auth is None or self._face_auth.trusted_count == 0:
            return False
        interval = 1.0 / self._config.camera.fps
        saw_trusted = False
        frame = first_frame
        for i in range(self._config.security.trusted_face_frames):
            if i > 0:
                time.sleep(interval)
                frame = self._camera.read_frame()
            if frame is None:
                continue
            verdict = self._face_auth.classify(frame)
            if verdict == "unknown":
                return False
            if verdict == "trusted":
                saw_trusted = True
        return saw_trusted

    def shutdown(self) -> None:
        self.stop_monitoring()
        self._logger.info("X9 encerrado")

    def _ausencia_confirmada(self, now: float) -> bool:
        """Verdadeiro quando ninguem e detectado ha tempo suficiente."""
        if self._last_detection_at is None:
            return False
        return now - self._last_detection_at >= self._config.detector.absence_seconds

    def _monitor_loop(self) -> None:
        interval = 1.0 / self._config.camera.fps

        while not self._stop_event.is_set():
            loop_start = time.monotonic()
            frame = self._camera.read_frame()

            if frame is None:
                self._tray.update_status(camera_ok=False)
                time.sleep(interval)
                continue

            now = time.time()
            detected, _confidence = self._detector.detect_person(frame)
            self._temporal_filter.push(now, detected)

            if detected:
                self._last_detection_at = now

            if self._temporal_filter.is_confirmed():
                locked = False
                extra_info = ""
                trusted = self._check_trusted(frame)
                if trusted:
                    # Mesmo confiavel, avisa: reconhecimento facial sem
                    # deteccao de pessoa viva pode ser enganado por foto.
                    extra_info = "pessoa confiavel reconhecida, PC NAO bloqueado"
                elif self._config.security.lock_on_detection:
                    locked = self._lock_screen()
                    extra_info = "PC bloqueado" if locked else "FALHA ao bloquear o PC"

                # Estranho logo depois de um alerta de pessoa confiavel tem que
                # avisar na hora: o cooldown aberto pelo alerta do dono nao pode
                # engolir a chegada de outra pessoa.
                force = locked or (not trusted and self._last_alert_trusted)
                sent = self._notifier.notify(extra_info, force=force)
                if sent:
                    self._last_alert_trusted = trusted
                if sent:
                    self._alert_count += 1
                    self._tray.update_status(
                        last_presence=datetime.now().strftime("%H:%M"),
                        alert_count=self._alert_count,
                    )
                self._temporal_filter.reset()

                if locked:
                    # Para sozinho: quem desbloquear com a senha e o dono,
                    # e continuar vigiando bloquearia de novo em segundos.
                    self._camera.release()
                    self._tray.update_status(monitoring=False)
                    self._logger.info("PC bloqueado, monitoramento parado")
                    return
            elif self._ausencia_confirmada(now):
                # A pessoa foi embora. Libera o cooldown para que a proxima
                # chegada gere alerta na hora, em vez de ficar engolida pelo
                # resto da janela de cooldown.
                self._notifier.rearm()
                self._last_detection_at = None

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

    face_auth = None
    det_model = resource_path("models/face_detection_yunet_2023mar.onnx")
    rec_model = resource_path("models/face_recognition_sface_2021dec.onnx")
    if det_model.exists() and rec_model.exists():
        face_auth = FaceAuth(
            det_model,
            rec_model,
            data_dir / "trusted_faces.npy",
            threshold=config.security.trusted_face_threshold,
        )
    else:
        logging.getLogger("x9.main").warning(
            "Modelos de rosto ausentes, reconhecimento de pessoa confiavel desligado"
        )

    agent = X9Agent(config, model_path, config_path, face_auth)
    agent.run()


if __name__ == "__main__":
    main()
