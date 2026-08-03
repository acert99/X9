import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from temporal_filter import TemporalFilter  # noqa: E402


def test_nao_confirma_abaixo_do_minimo():
    tf = TemporalFilter(window_seconds=3, positive_frames_required=5)
    t = 0.0
    for _ in range(4):
        tf.push(t, True)
        t += 1 / 3
    assert tf.is_confirmed() is False


def test_confirma_ao_atingir_o_minimo():
    tf = TemporalFilter(window_seconds=3, positive_frames_required=5)
    t = 0.0
    for _ in range(5):
        tf.push(t, True)
        t += 1 / 3
    assert tf.is_confirmed() is True


def test_padrao_intermitente_nao_confirma():
    tf = TemporalFilter(window_seconds=3, positive_frames_required=5)
    t = 0.0
    for v in [True, False, True, False, True]:
        tf.push(t, v)
        t += 1 / 3
    assert tf.is_confirmed() is False


def test_janela_expira_deteccoes_antigas():
    tf = TemporalFilter(window_seconds=3, positive_frames_required=3)
    tf.push(0.0, True)
    tf.push(0.5, True)
    tf.push(1.0, True)
    tf.push(5.0, True)
    tf.push(5.3, True)
    assert tf.is_confirmed() is False


def test_reset_limpa_o_historico():
    tf = TemporalFilter(window_seconds=3, positive_frames_required=2)
    tf.push(0.0, True)
    tf.push(0.5, True)
    assert tf.is_confirmed() is True
    tf.reset()
    assert tf.is_confirmed() is False
