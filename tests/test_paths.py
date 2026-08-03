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
    assert data_dir == tmp_path / "localappdata" / "X9"
    assert data_dir.is_dir()


def _modo_executavel(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path / "meipass"), raising=False)
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "localappdata"))
    return tmp_path / "localappdata"


def test_migra_config_da_instalacao_com_nome_antigo(tmp_path, monkeypatch):
    base = _modo_executavel(tmp_path, monkeypatch)
    antiga = base / "PresenceAgent"
    antiga.mkdir(parents=True)
    (antiga / "config.yaml").write_text("conteudo antigo", encoding="utf-8")

    data_dir = paths.user_data_dir()

    # a config antiga e aproveitada, e a pasta antiga fica intacta
    assert (data_dir / "config.yaml").read_text(encoding="utf-8") == "conteudo antigo"
    assert (antiga / "config.yaml").is_file()


def test_migracao_nao_sobrescreve_config_ja_existente(tmp_path, monkeypatch):
    base = _modo_executavel(tmp_path, monkeypatch)
    antiga = base / "PresenceAgent"
    antiga.mkdir(parents=True)
    (antiga / "config.yaml").write_text("conteudo antigo", encoding="utf-8")
    nova = base / "X9"
    nova.mkdir(parents=True)
    (nova / "config.yaml").write_text("conteudo novo", encoding="utf-8")

    data_dir = paths.user_data_dir()

    assert (data_dir / "config.yaml").read_text(encoding="utf-8") == "conteudo novo"


def test_sem_instalacao_antiga_nao_cria_config(tmp_path, monkeypatch):
    _modo_executavel(tmp_path, monkeypatch)

    data_dir = paths.user_data_dir()

    assert not (data_dir / "config.yaml").exists()
