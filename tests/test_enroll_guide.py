import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from enroll_guide import STEPS, GuidedEnrollment, Pose  # noqa: E402

EMB = np.zeros(128, dtype=np.float32)
FRENTE = Pose(yaw=0.0, pitch=0.5, size=0.30)


def _passar_frente(g):
    for _ in range(g.samples_per_step):
        assert g.feed(FRENTE, EMB)


def test_roteiro_completo_aceita_poses_certas():
    g = GuidedEnrollment()
    _passar_frente(g)
    for pose in [
        Pose(0.25, 0.5, 0.30),   # lado 1
        Pose(-0.25, 0.5, 0.30),  # lado 2 (oposto)
        Pose(0.0, 0.40, 0.30),   # queixo 1
        Pose(0.0, 0.60, 0.30),   # queixo 2 (oposto)
        Pose(0.0, 0.5, 0.40),    # perto
        Pose(0.0, 0.5, 0.20),    # longe
    ]:
        for _ in range(g.samples_per_step):
            assert g.feed(pose, EMB), (g.current.key, pose)
    assert g.done
    assert len(g.accepted) == len(STEPS) * g.samples_per_step


def test_frente_recusa_rosto_virado():
    g = GuidedEnrollment()
    assert not g.feed(Pose(0.3, 0.5, 0.3), EMB)


def test_segundo_lado_tem_que_ser_o_oposto():
    g = GuidedEnrollment()
    _passar_frente(g)
    for _ in range(g.samples_per_step):
        g.feed(Pose(0.25, 0.5, 0.3), EMB)
    assert g.current.key == "side2"
    assert not g.feed(Pose(0.25, 0.5, 0.3), EMB), "mesmo lado nao vale"
    assert g.feed(Pose(-0.25, 0.5, 0.3), EMB)


def test_espelhado_funciona_igual():
    """Camera espelhada inverte o sinal do yaw; o roteiro nao liga."""
    g = GuidedEnrollment()
    _passar_frente(g)
    for _ in range(g.samples_per_step):
        assert g.feed(Pose(-0.25, 0.5, 0.3), EMB)
    assert g.feed(Pose(0.25, 0.5, 0.3), EMB)


def test_pular_nao_pula_a_etapa_de_frente():
    g = GuidedEnrollment()
    g.skip()
    assert g.current.key == "front"
    _passar_frente(g)
    g.skip()
    assert g.current.key == "side2"


def test_perto_e_longe_relativos_a_frente():
    g = GuidedEnrollment()
    _passar_frente(g)
    for _ in range(4):
        g.skip()
    assert g.current.key == "near"
    assert not g.feed(Pose(0.0, 0.5, 0.33), EMB), "10% maior ainda nao e perto"
    assert g.feed(Pose(0.0, 0.5, 0.40), EMB)
