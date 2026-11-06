"""
Assistente de primeira execucao.

Se ainda nao existir um config.yaml na pasta de dados do usuario,
mostra uma janela simples pedindo a URL de notificacao (formato
aceito pelo Apprise) e grava o arquivo com os demais valores no
padrao recomendado. Depois disso o programa nunca mais pergunta,
a menos que o arquivo seja apagado.

Isso elimina a necessidade de editar config.yaml a mao depois que
o executavel ja foi gerado.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox
from pathlib import Path

DEFAULT_TEMPLATE = """camera:
  index: 0
  width: 640
  height: 480
  fps: 3
  open_retries: 3
  open_retry_delay_seconds: 2.0

detector:
  input_size: 416
  confidence: 0.60
  nms_threshold: 0.45
  positive_frames: 5
  window_seconds: 3
  absence_seconds: 60

notification:
  cooldown_seconds: 600
  title: "X9"
  message: "Presenca detectada no computador"
  urls:
    - "{notification_url}"

security:
  # Bloqueia o Windows (igual Win+L) ao detectar alguem e para o
  # monitoramento. Para vigiar de novo, inicie pela bandeja.
  lock_on_detection: true
  # Pessoa confiavel: cadastre seu rosto pela bandeja. Reconhecido, o X9
  # avisa mas nao bloqueia. Mais alto = mais exigente (0 a 1).
  trusted_face_threshold: 0.45
  trusted_face_frames: 6

logging:
  level: INFO
"""

PLACEHOLDER_URL = "ntfy://ntfy.sh/"


def render_config(notification_url: str) -> str:
    """Gera o conteudo do config.yaml a partir do template.

    Separado da parte grafica de proposito, para poder ser testado
    sem precisar abrir nenhuma janela.
    """
    return DEFAULT_TEMPLATE.format(notification_url=notification_url)


def run_first_time_setup(config_path: Path) -> bool:
    """Mostra o assistente grafico. Retorna True se o usuario concluiu."""
    result: dict[str, str | None] = {"url": None}

    root = tk.Tk()
    root.title("X9 - Configuracao inicial")
    root.resizable(False, False)

    tk.Label(
        root,
        text=(
            "Antes de comecar, informe para onde enviar as notificacoes.\n"
            "Exemplo usando o app ntfy (gratuito):\n"
            "ntfy://ntfy.sh/um_nome_dificil_de_adivinhar\n\n"
            "Instale o app ntfy no celular e inscreva no mesmo topico."
        ),
        justify="left",
        padx=16,
        pady=12,
    ).pack()

    entry = tk.Entry(root, width=50)
    entry.insert(0, PLACEHOLDER_URL)
    entry.pack(padx=16, pady=(0, 12))
    entry.focus_set()
    entry.icursor(tk.END)

    def confirmar() -> None:
        url = entry.get().strip()
        if not url or url == PLACEHOLDER_URL:
            messagebox.showwarning(
                "X9", "Preencha uma URL de notificacao valida."
            )
            return
        result["url"] = url
        root.destroy()

    def cancelar() -> None:
        root.destroy()

    button_frame = tk.Frame(root)
    button_frame.pack(pady=(0, 16))
    tk.Button(button_frame, text="Cancelar", width=12, command=cancelar).pack(
        side="left", padx=6
    )
    tk.Button(button_frame, text="Concluir", width=12, command=confirmar).pack(
        side="left", padx=6
    )

    root.mainloop()

    if result["url"] is None:
        return False

    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(render_config(result["url"]), encoding="utf-8")
    return True
