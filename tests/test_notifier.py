import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from notifier import NotificationService  # noqa: E402


def _servico(cooldown=600):
    servico = NotificationService(urls=[], cooldown_seconds=cooldown)
    # Sem URLs reais: o envio e simulado para o teste nao depender de rede.
    servico._apprise.notify = lambda **kwargs: True
    return servico


def test_primeiro_alerta_e_enviado():
    assert _servico().notify() is True


def test_segundo_alerta_dentro_do_cooldown_e_suprimido():
    servico = _servico()
    assert servico.notify() is True
    assert servico.notify() is False


def test_rearm_libera_alerta_antes_do_cooldown_expirar():
    """Cenario real: pessoa detectada, sai, e volta dentro do cooldown.

    Sem o rearm a segunda chegada ficava sem alerta por ate 10 minutos,
    justamente o evento que o usuario precisa saber.
    """
    servico = _servico()
    assert servico.notify() is True
    assert servico.notify() is False

    assert servico.rearm() is True
    assert servico.notify() is True


def test_rearm_sem_alerta_previo_nao_faz_nada():
    servico = _servico()
    assert servico.rearm() is False


def test_cooldown_volta_a_valer_depois_do_rearm():
    """O rearm libera um alerta, nao desliga o cooldown permanentemente."""
    servico = _servico()
    servico.notify()
    servico.rearm()
    assert servico.notify() is True
    assert servico.notify() is False


def test_cooldown_expira_por_tempo():
    servico = _servico(cooldown=100)
    with patch("notifier.time.time", side_effect=[0.0, 200.0]):
        assert servico.notify() is True
        assert servico.notify() is True
