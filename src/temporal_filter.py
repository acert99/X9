"""
TemporalFilter

So confirma presenca se houver um numero minimo de deteccoes
positivas dentro de uma janela de tempo. Isso evita alertas
disparados por um unico frame com falso positivo.

Nao sabe nada sobre camera, modelo ou notificacao. Recebe apenas
booleanos com timestamp e responde se a janela atual confirma
presenca ou nao.
"""

from __future__ import annotations

from collections import deque
from typing import Deque, Tuple


class TemporalFilter:
    def __init__(self, window_seconds: float, positive_frames_required: int) -> None:
        self._window_seconds = window_seconds
        self._positive_frames_required = positive_frames_required
        self._events: Deque[Tuple[float, bool]] = deque()

    def push(self, timestamp: float, detected: bool) -> None:
        self._events.append((timestamp, detected))
        self._purge_old(timestamp)

    def is_confirmed(self) -> bool:
        positives = sum(1 for _, detected in self._events if detected)
        return positives >= self._positive_frames_required

    def reset(self) -> None:
        self._events.clear()

    def _purge_old(self, current_timestamp: float) -> None:
        cutoff = current_timestamp - self._window_seconds
        while self._events and self._events[0][0] < cutoff:
            self._events.popleft()
