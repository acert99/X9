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
    SecurityConfig,
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


def _montar_agente(absence_seconds, fps, bloquear=False):
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
        security=SecurityConfig(lock_on_detection=bloquear),
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
    # Nunca usar o bloqueio real aqui: travaria o PC de quem roda os testes.
    agente.bloqueios = []
    agente._lock_screen = lambda: agente.bloqueios.append(1) or True
    agente._face_auth = None
    agente._last_alert_trusted = False
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


def test_loop_bloqueia_pc_e_para_ao_detectar():
    agente, enviados = _montar_agente(absence_seconds=1.0, fps=50, bloquear=True)
    thread = threading.Thread(target=agente._monitor_loop, daemon=True)
    agente._detector.tem_pessoa = True
    thread.start()
    thread.join(timeout=3)

    assert not thread.is_alive(), "loop deveria parar sozinho depois de bloquear"
    assert len(agente.bloqueios) == 1
    assert len(enviados) == 1


def test_loop_sem_bloqueio_continua_vigiando():
    agente, enviados = _montar_agente(absence_seconds=1.0, fps=50, bloquear=False)
    _rodar(agente, enviados, [(1.0, True)])

    assert agente.bloqueios == []
    assert len(enviados) == 1


class _FaceAuthFalso:
    def __init__(self, veredito):
        self.veredito = veredito
        self.trusted_count = 1

    def classify(self, frame):
        return self.veredito


def test_pessoa_confiavel_avisa_mas_nao_bloqueia():
    agente, enviados = _montar_agente(absence_seconds=1.0, fps=50, bloquear=True)
    agente._face_auth = _FaceAuthFalso("trusted")
    thread = threading.Thread(target=agente._monitor_loop, daemon=True)
    agente._detector.tem_pessoa = True
    thread.start()
    time.sleep(1.5)

    assert thread.is_alive(), "com pessoa confiavel o X9 continua vigiando"
    agente._stop_event.set()
    thread.join(timeout=5)
    assert agente.bloqueios == []
    assert len(enviados) == 1


def test_rosto_desconhecido_bloqueia():
    agente, enviados = _montar_agente(absence_seconds=1.0, fps=50, bloquear=True)
    agente._face_auth = _FaceAuthFalso("unknown")
    thread = threading.Thread(target=agente._monitor_loop, daemon=True)
    agente._detector.tem_pessoa = True
    thread.start()
    thread.join(timeout=3)

    assert len(agente.bloqueios) == 1


def test_sem_rosto_visivel_conta_como_estranho():
    agente, enviados = _montar_agente(absence_seconds=1.0, fps=50, bloquear=True)
    agente._face_auth = _FaceAuthFalso("no_face")
    thread = threading.Thread(target=agente._monitor_loop, daemon=True)
    agente._detector.tem_pessoa = True
    thread.start()
    thread.join(timeout=3)

    assert len(agente.bloqueios) == 1


def test_bloqueio_avisa_mesmo_em_cooldown():
    agente, enviados = _montar_agente(absence_seconds=1.0, fps=50, bloquear=True)
    agente._notifier.notify()  # coloca em cooldown
    enviados.clear()
    thread = threading.Thread(target=agente._monitor_loop, daemon=True)
    agente._detector.tem_pessoa = True
    thread.start()
    thread.join(timeout=3)

    assert len(agente.bloqueios) == 1
    assert len(enviados) == 1, "aviso de bloqueio tem que sair mesmo em cooldown"


class _FaceAuthRoteiro:
    """Devolve vereditos em sequencia: simula o dono saindo e um
    estranho sentando logo em seguida."""

    def __init__(self, vereditos):
        self.vereditos = list(vereditos)
        self.trusted_count = 1

    def classify(self, frame):
        return self.vereditos.pop(0) if len(self.vereditos) > 1 else self.vereditos[0]


def test_estranho_depois_do_dono_avisa_mesmo_sem_bloqueio():
    """Alerta de 'pessoa confiavel' nao pode engolir, pelo cooldown, o
    alerta de um estranho que senta logo depois."""
    agente, enviados = _montar_agente(absence_seconds=60.0, fps=50, bloquear=False)
    agente._config.security.trusted_face_frames = 1
    agente._face_auth = _FaceAuthRoteiro(["trusted", "unknown"])
    _rodar(agente, enviados, [(1.5, True)])

    assert len(enviados) == 2, f"esperado alerta do dono e do estranho, veio {len(enviados)}"
