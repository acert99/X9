import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import paths  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def test_modo_desenvolvimento_usa_raiz_do_projeto():
    assert paths.is_frozen() is False
    assert paths.user_data_dir() == PROJECT_ROOT
    assert paths.resource_path("models/yolox_nano.onnx") == (
        PROJECT_ROOT / "models" / "yolox_nano.onnx"
    )


def test_modo_executavel_usa_pasta_de_dados_do_usuario(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path / "meipass"), raising=False)
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "localappdata"))

    assert paths.is_frozen() is True
    assert str(paths.resource_path("models/yolox_nano.onnx")).startswith(
        str(tmp_path / "meipass")
    )

    data_dir = paths.user_data_dir()
    assert data_dir == tmp_path / "localappdata" / "PresenceAgent"
    assert data_dir.is_dir()
