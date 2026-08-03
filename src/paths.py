"""
Resolve caminhos de recursos empacotados e o diretorio de dados do
usuario.

Quando roda como script Python normal (`python src/main.py`), tudo
fica dentro da propria pasta do projeto, igual antes. Quando roda
como executavel gerado pelo PyInstaller, os recursos empacotados
(o modelo ONNX, por exemplo) ficam num diretorio temporario apontado
por sys._MEIPASS, e os dados do usuario que precisam ser gravaveis
e persistentes entre execucoes (config.yaml, log) ficam numa pasta
separada fora desse temporario.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def is_frozen() -> bool:
    return getattr(sys, "frozen", False)


def resource_path(relative: str) -> Path:
    """Caminho para um recurso empacotado junto do executavel, somente leitura."""
    if is_frozen():
        base = Path(getattr(sys, "_MEIPASS"))
    else:
        base = Path(__file__).resolve().parent.parent
    return base / relative


def user_data_dir() -> Path:
    """Pasta gravavel e persistente para config.yaml e arquivo de log.

    Em modo desenvolvimento essa pasta e a raiz do proprio projeto,
    para manter o comportamento de antes. Em modo executavel, usa a
    pasta padrao de dados de aplicativo do usuario no Windows.
    """
    if not is_frozen():
        return Path(__file__).resolve().parent.parent

    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", str(Path.home())))
    else:
        base = Path.home() / ".local" / "share"

    data_dir = base / "PresenceAgent"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir
