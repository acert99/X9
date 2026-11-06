import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from face_auth import decide  # noqa: E402


def _vec(*valores):
    v = np.zeros(128, dtype=np.float32)
    v[: len(valores)] = valores
    return v / np.linalg.norm(v)


DONO = _vec(1, 0)
ESTRANHO = _vec(0, 1)
CADASTRO = np.array([DONO])


def test_dono_sozinho_e_confiavel():
    assert decide(np.array([DONO]), CADASTRO, 0.45)[0] == "trusted"


def test_estranho_e_desconhecido():
    assert decide(np.array([ESTRANHO]), CADASTRO, 0.45)[0] == "unknown"


def test_dono_com_estranho_ao_lado_nao_e_confiavel():
    assert decide(np.array([DONO, ESTRANHO]), CADASTRO, 0.45)[0] == "unknown"


def test_sem_rosto_visivel():
    vazio = np.zeros((0, 128), dtype=np.float32)
    assert decide(vazio, CADASTRO, 0.45)[0] == "no_face"


def test_sem_ninguem_cadastrado_nunca_e_confiavel():
    vazio = np.zeros((0, 128), dtype=np.float32)
    assert decide(np.array([DONO]), vazio, 0.45)[0] == "unknown"


def test_limite_controla_exigencia():
    parecido = _vec(1, 1)  # similaridade ~0.71 com o dono
    assert decide(np.array([parecido]), CADASTRO, 0.60)[0] == "trusted"
    assert decide(np.array([parecido]), CADASTRO, 0.80)[0] == "unknown"
