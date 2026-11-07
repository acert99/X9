"""
Janela do cadastro guiado de rosto.

Mostra a camera ao vivo (espelhada, como num espelho), a instrucao da
etapa atual e o progresso. Cada frame passa pelo detector de rostos; se
a pose bate com a etapa (ver enroll_guide), a amostra e aceita. Etapa
que nao sai em ETAPA_TIMEOUT segundos e pulada sozinha, para ninguem
ficar preso.

Nada e gravado em disco aqui: as amostras aceitas (so vetores) sao
devolvidas para quem chamou, que decide salvar.
"""

from __future__ import annotations

import logging
import time
import tkinter as tk
from typing import Callable, List, Optional

import cv2
import numpy as np
from PIL import Image, ImageTk

from camera import CameraManager
from enroll_guide import STEPS, GuidedEnrollment, pose_from_face
from face_auth import FaceAuth

logger = logging.getLogger("x9.enroll")

PREVIEW_W, PREVIEW_H = 480, 360
ETAPA_TIMEOUT = 12.0
INTERVALO_AMOSTRAS = 0.35  # segundos entre amostras da mesma etapa
COR_OK = (67, 160, 46)     # BGR
COR_ESPERA = (40, 140, 242)


def run_guided_enrollment(
    camera: CameraManager, face_auth: FaceAuth
) -> Optional[List[np.ndarray]]:
    """Abre a janela e bloqueia ate fechar.

    Retorna as amostras aceitas, ou None se o usuario cancelou ou a
    camera nao abriu.
    """
    if not camera.open():
        return None

    guide = GuidedEnrollment()
    state = {"cancelled": False, "step_started": time.monotonic(), "last_sample": 0.0}

    root = tk.Tk()
    root.title("X9 - Cadastrar meu rosto")
    root.resizable(False, False)
    root.attributes("-topmost", True)
    root.configure(bg="#2b2b2b")

    instr = tk.Label(
        root, text="", font=("Segoe UI", 16, "bold"), fg="#f28c28", bg="#2b2b2b", pady=8
    )
    instr.pack(fill="x")
    video = tk.Label(root, bg="#000000")
    video.pack(padx=12)
    status = tk.Label(root, text="", font=("Segoe UI", 11), fg="#e0e0e0", bg="#2b2b2b", pady=6)
    status.pack(fill="x")

    buttons = tk.Frame(root, bg="#2b2b2b")
    buttons.pack(pady=(0, 12))

    def pular() -> None:
        guide.skip()
        state["step_started"] = time.monotonic()

    def cancelar() -> None:
        state["cancelled"] = True
        root.destroy()

    btn_pular = tk.Button(buttons, text="Pular etapa", width=14, command=pular)
    btn_pular.pack(side="left", padx=6)
    tk.Button(buttons, text="Cancelar", width=14, command=cancelar).pack(side="left", padx=6)
    root.protocol("WM_DELETE_WINDOW", cancelar)

    def tick() -> None:
        if guide.done:
            instr.config(text="Pronto!")
            status.config(text=f"{len(guide.accepted)} amostras cadastradas.")
            root.after(1500, root.destroy)
            return

        frame = camera.read_frame()
        if frame is None:
            root.after(100, tick)
            return

        now = time.monotonic()
        step = guide.current
        faces = face_auth.detect(frame)
        cor = COR_ESPERA
        aviso = ""

        if len(faces) == 1:
            face = faces[0]
            pose = pose_from_face(face, frame.shape[1])
            if guide.matches(pose):
                cor = COR_OK
                if now - state["last_sample"] >= INTERVALO_AMOSTRAS:
                    if guide.feed(pose, face_auth.embed(frame, face)):
                        state["last_sample"] = now
                        if guide.current is not step:
                            state["step_started"] = now
            x, y, w, h = (int(v) for v in face[:4])
            cv2.rectangle(frame, (x, y), (x + w, y + h), cor, 3)
        elif len(faces) == 0:
            aviso = "Nao estou vendo seu rosto"
        else:
            aviso = "Fique sozinho na frente da camera"

        if (
            guide.current is step
            and step.key != "front"
            and now - state["step_started"] > ETAPA_TIMEOUT
        ):
            logger.info("Etapa %s pulada por tempo", step.key)
            guide.skip()
            state["step_started"] = now

        if not guide.done:
            feitas, total = guide.progress
            instr.config(text=guide.current.instruction)
            btn_pular.config(state="disabled" if guide.current.key == "front" else "normal")
            status.config(
                text=aviso
                or f"Etapa {guide.step_index + 1} de {len(STEPS)}  ·  "
                f"amostras {feitas}/{total}  ·  verde = pose certa"
            )

        # Espelha so para exibir: a pessoa se ve como num espelho.
        rgb = cv2.cvtColor(cv2.flip(frame, 1), cv2.COLOR_BGR2RGB)
        img = Image.fromarray(rgb).resize((PREVIEW_W, PREVIEW_H))
        photo = ImageTk.PhotoImage(img)
        video.configure(image=photo)
        video.image = photo  # segura a referencia, senao o Tk apaga a imagem
        root.after(60, tick)

    try:
        root.after(0, tick)
        root.mainloop()
    finally:
        camera.release()

    if state["cancelled"]:
        return None
    return guide.accepted
