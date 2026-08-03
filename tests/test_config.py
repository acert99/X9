import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from config import Config  # noqa: E402


def test_carrega_configuracao_valida(tmp_path):
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        """
camera:
  fps: 3
notification:
  urls:
    - "ntfy://ntfy.sh/teste"
"""
    )
    cfg = Config.load(config_file)
    assert cfg.camera.fps == 3
    assert cfg.notification.urls == ["ntfy://ntfy.sh/teste"]
    # valores default aplicados quando nao especificados
    assert cfg.camera.width == 640
    assert cfg.detector.positive_frames == 5


def test_rejeita_sem_urls_de_notificacao(tmp_path):
    config_file = tmp_path / "config.yaml"
    config_file.write_text("notification:\n  urls: []\n")
    with pytest.raises(ValueError):
        Config.load(config_file)


def test_rejeita_arquivo_inexistente(tmp_path):
    with pytest.raises(FileNotFoundError):
        Config.load(tmp_path / "nao_existe.yaml")


def test_rejeita_fps_zero(tmp_path):
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        """
camera:
  fps: 0
notification:
  urls:
    - "ntfy://ntfy.sh/teste"
"""
    )
    with pytest.raises(ValueError):
        Config.load(config_file)
