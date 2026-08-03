"""Exercita o loop real do X9Agent, nao uma copia da logica.

Usa camera e detector falsos, e parametros comprimidos (fps alto,
absence_seconds curto) para o ciclo chegada -> saida -> chegada rodar em
poucos segundos em vez dos minutos que levaria com os valores reais.
"""

import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from config import (  # noqa: E402
    CameraConfig,
    Config,
    DetectorConfig,
    NotificationConfig,
)
from main import X9Agent  # noqa: E402
from notifier import NotificationService  # noqa: E402
from temporal_filter import TemporalFilter  # noqa: E402


class _CameraFalsa:
    def read_frame(self):
        return object()  # o detector falso ignora o conteudo

    def release(self):
        pass


class _DetectorFalso:
    """Devolve o que o teste mandar, controlado por um sinalizador."""

    def __init__(self):
        self.tem_pessoa = False

    def detect_person(self, frame):
        return self.tem_pessoa, 0.9 if self.tem_pessoa else 0.0


class _TrayFalsa:
    def update_status(self, **kwargs):
        pass


def _montar_agente(absence_seconds, fps):
    config = Config(
        camera=CameraConfig(fps=fps),
        detector=DetectorConfig(
            positive_frames=3,
            window_seconds=1.0,
            absence_seconds=absence_seconds,
        ),
        notification=NotificationConfig(
            cooldown_seconds=600, urls=["ntfy://ntfy.sh/teste"]
        ),
    )

    agente = object.__new__(X9Agent)
    agente._config = config
    agente._camera = _CameraFalsa()
    agente._detector = _DetectorFalso()
    agente._tray = _TrayFalsa()
    agente._temporal_filter = TemporalFilter(
        window_seconds=config.detector.window_seconds,
        positive_frames_required=config.detector.positive_frames,
    )
    agente._notifier = NotificationService(
        urls=[], cooldown_seconds=config.notification.cooldown_seconds
    )

    enviados = []
    agente._notifier._apprise.notify = lambda **kwargs: enviados.append(1) or True

    import logging

    agente._logger = logging.getLogger("teste")
    agente._stop_event = threading.Event()
    agente._alert_count = 0
    agente._last_detection_at = None
    return agente, enviados


def _rodar(agente, enviados, roteiro):
    """roteiro: lista de (segundos, tem_pessoa)."""
    thread = threading.Thread(target=agente._monitor_loop, daemon=True)
    thread.start()
    try:
        for segundos, tem_pessoa in roteiro:
            agente._detector.tem_pessoa = tem_pessoa
            time.sleep(segundos)
    finally:
        agente._stop_event.set()
        thread.join(timeout=5)
    return len(enviados)


def test_loop_alerta_de_novo_apos_ausencia():
    """Chegada, saida prolongada, nova chegada -> dois alertas."""
    agente, enviados = _montar_agente(absence_seconds=1.0, fps=50)
    total = _rodar(agente, enviados, [(1.0, True), (2.0, False), (1.0, True)])

    assert total == 2, f"esperado 2 alertas, veio {total}"


def test_loop_nao_repete_alerta_com_pessoa_parada():
    agente, enviados = _montar_agente(absence_seconds=1.0, fps=50)
    total = _rodar(agente, enviados, [(3.0, True)])

    assert total == 1, f"esperado 1 alerta, veio {total}"
