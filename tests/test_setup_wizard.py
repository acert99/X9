import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from config import Config  # noqa: E402
from setup_wizard import render_config  # noqa: E402


def test_render_config_gera_yaml_valido(tmp_path):
    log_path = tmp_path / "presence_agent.log"
    content = render_config("ntfy://ntfy.sh/teste", log_path)

    config_file = tmp_path / "config.yaml"
    config_file.write_text(content, encoding="utf-8")

    cfg = Config.load(config_file)
    assert cfg.notification.urls == ["ntfy://ntfy.sh/teste"]
    assert cfg.camera.fps == 3


def test_render_config_converte_barras_invertidas_do_windows(tmp_path):
    log_path = Path("C:\\Users\\alguem\\PresenceAgent\\presence_agent.log")

    content = render_config("ntfy://ntfy.sh/teste", log_path)

    assert "\\" not in content
    assert "C:/Users/alguem" in content
