import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from config import Config  # noqa: E402
from setup_wizard import render_config  # noqa: E402


def test_render_config_gera_yaml_valido(tmp_path):
    content = render_config("ntfy://ntfy.sh/teste")

    config_file = tmp_path / "config.yaml"
    config_file.write_text(content, encoding="utf-8")

    cfg = Config.load(config_file)
    assert cfg.notification.urls == ["ntfy://ntfy.sh/teste"]
    assert cfg.camera.fps == 3


def test_config_gerado_nao_persiste_caminho_absoluto():
    """Caminhos absolutos em config quebram quando a pasta muda.

    Ja aconteceu duas vezes neste projeto: com o modelo (pasta _MEI do
    PyInstaller, nova a cada execucao) e com o log (pasta renomeada de
    PresenceAgent para X9). Modelo e log agora sao resolvidos em tempo
    de execucao, entao nenhum caminho deve aparecer no arquivo gerado.
    """
    content = render_config("ntfy://ntfy.sh/teste")

    assert "\\" not in content
    assert ":/" not in content.replace("ntfy://", "").replace("://", "")
    assert "model_path" not in content
    assert "file:" not in content
