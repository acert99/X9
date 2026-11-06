"""
CameraManager

Responsavel apenas por abrir, ler frames e liberar a webcam.
Nao sabe nada sobre deteccao, notificacao ou interface.
"""

from __future__ import annotations

import logging
import sys
import time
from typing import List, Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger("x9.camera")

# DirectShow no Windows: cameras virtuais (iVCam, OBS Virtual Camera,
# DroidCam) costumam ser so DirectShow, e o backend padrao do OpenCV
# (MSMF) nao as enxerga. Usar o mesmo backend em todo lugar tambem faz
# o indice bater com a ordem da lista de nomes em list_cameras().
_BACKEND = cv2.CAP_DSHOW if sys.platform == "win32" else cv2.CAP_ANY


def list_cameras(max_probe: int = 5) -> List[Tuple[int, str]]:
    """Lista as cameras disponiveis como (indice, nome)."""
    if sys.platform == "win32":
        try:
            from pygrabber.dshow_graph import FilterGraph

            return list(enumerate(FilterGraph().get_input_devices()))
        except Exception:
            logger.exception("Falha ao listar cameras pelo DirectShow")

    # Sem nomes: testa os indices um a um.
    found = []
    for index in range(max_probe):
        cap = cv2.VideoCapture(index, _BACKEND)
        if cap.isOpened():
            found.append((index, f"Camera {index}"))
        cap.release()
    return found


class CameraManager:
    def __init__(
        self,
        index: int = 0,
        width: int = 640,
        height: int = 480,
        fps: int = 3,
        open_retries: int = 3,
        open_retry_delay_seconds: float = 2.0,
    ) -> None:
        self._index = index
        self._width = width
        self._height = height
        self._fps = fps
        self._open_retries = open_retries
        self._open_retry_delay_seconds = open_retry_delay_seconds
        self._cap: Optional[cv2.VideoCapture] = None

    def open(self) -> bool:
        """Tenta abrir a webcam com algumas tentativas antes de desistir.

        Retorna True se conseguiu abrir, False caso contrario.
        """
        for attempt in range(1, self._open_retries + 1):
            cap = cv2.VideoCapture(self._index, _BACKEND)
            if cap.isOpened():
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, self._width)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self._height)
                cap.set(cv2.CAP_PROP_FPS, self._fps)
                self._cap = cap
                logger.info("Camera %s aberta na tentativa %d", self._index, attempt)
                return True

            cap.release()
            logger.warning(
                "Falha ao abrir camera %s (tentativa %d de %d)",
                self._index,
                attempt,
                self._open_retries,
            )
            if attempt < self._open_retries:
                time.sleep(self._open_retry_delay_seconds)

        logger.error("Nao foi possivel abrir a camera %s", self._index)
        return False

    @property
    def index(self) -> int:
        return self._index

    def set_index(self, index: int) -> None:
        """Troca a camera. Vale na proxima vez que open() for chamado."""
        self.release()
        self._index = index

    def is_opened(self) -> bool:
        return self._cap is not None and self._cap.isOpened()

    def read_frame(self) -> Optional[np.ndarray]:
        """Le um frame. Retorna None se a leitura falhar ou a camera nao estiver aberta."""
        if not self.is_opened():
            return None

        ok, frame = self._cap.read()
        if not ok:
            logger.warning("Falha ao ler frame da camera %s", self._index)
            return None
        return frame

    def release(self) -> None:
        if self._cap is not None:
            self._cap.release()
            self._cap = None
            logger.info("Camera %s liberada", self._index)

    def __enter__(self) -> "CameraManager":
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.release()
