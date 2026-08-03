"""Cobre o ciclo chegada -> saida -> nova chegada.

Este e o cenario que motivou o rearm: sem ele, a segunda chegada ficava
sem alerta por ate o cooldown inteiro (10 minutos por padrao).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from notifier import NotificationService  # noqa: E402
from temporal_filter import TemporalFilter  # noqa: E402

ABSENCE_SECONDS = 60.0
COOLDOWN = 600
FPS = 3.0


class _Cenario:
    """Roda a mesma logica de decisao do loop de monitoramento."""

    def __init__(self, absence_seconds=ABSENCE_SECONDS):
        self.absence_seconds = absence_seconds
        self.filtro = TemporalFilter(window_seconds=3.0, positive_frames_required=5)
        self.notificador = NotificationService(urls=[], cooldown_seconds=COOLDOWN)
        self.notificador._apprise.notify = lambda **kwargs: True
        self.ultima_deteccao = None
        self.alertas = []
        self.agora = 0.0

    def avancar(self, segundos, detectado):
        """Simula frames por N segundos com o detector devolvendo `detectado`."""
        for _ in range(int(segundos * FPS)):
            self.agora += 1.0 / FPS
            self.filtro.push(self.agora, detectado)
            if detectado:
                self.ultima_deteccao = self.agora

            if self.filtro.is_confirmed():
                if self.notificador.notify():
                    self.alertas.append(round(self.agora, 1))
                self.filtro.reset()
            elif (
                self.ultima_deteccao is not None
                and self.agora - self.ultima_deteccao >= self.absence_seconds
            ):
                self.notificador.rearm()
                self.ultima_deteccao = None


def test_chegada_saida_e_nova_chegada_geram_dois_alertas():
    c = _Cenario()
    c.avancar(10, detectado=True)      # alguem senta
    c.avancar(120, detectado=False)    # vai embora e some por 2 minutos
    c.avancar(10, detectado=True)      # alguem senta de novo

    assert len(c.alertas) == 2, f"esperado 2 alertas, veio {c.alertas}"


def test_pessoa_que_fica_sentada_nao_gera_alerta_repetido():
    """O cooldown continua fazendo seu trabalho contra spam."""
    c = _Cenario()
    c.avancar(300, detectado=True)

    assert len(c.alertas) == 1, f"esperado 1 alerta, veio {c.alertas}"


def test_ausencia_curta_nao_rearma():
    """Sair do enquadramento por instantes nao deve virar alerta novo."""
    c = _Cenario()
    c.avancar(10, detectado=True)
    c.avancar(20, detectado=False)     # 20s < absence_seconds de 60s
    c.avancar(10, detectado=True)

    assert len(c.alertas) == 1, f"esperado 1 alerta, veio {c.alertas}"


def test_sala_vazia_desde_o_inicio_nao_alerta():
    c = _Cenario()
    c.avancar(300, detectado=False)

    assert c.alertas == []
