"""
TrayInterface

Icone na bandeja do Windows com um menu simples: iniciar ou parar
o monitoramento, ver status (camera, detector, ultima presenca,
contagem de alertas) e sair do programa.

Nao sabe nada sobre camera, detector ou notificacao diretamente.
Apenas recebe callbacks (on_start, on_stop, on_exit) e um metodo
update_status para refletir o estado atual na interface.
"""

from __future__ import annotations

import logging
import threading
from typing import Callable, Optional

import pystray
from PIL import Image, ImageDraw

logger = logging.getLogger("presence_agent.tray")

COLOR_IDLE = (120, 120, 120)
COLOR_MONITORING = (46, 160, 67)
COLOR_ALERT = (200, 60, 60)


class TrayInterface:
    def __init__(
        self,
        on_start: Callable[[], None],
        on_stop: Callable[[], None],
        on_exit: Callable[[], None],
    ) -> None:
        self._on_start = on_start
        self._on_stop = on_stop
        self._on_exit = on_exit

        self._monitoring = False
        self._camera_ok = False
        self._detector_ok = False
        self._last_presence: Optional[str] = None
        self._alert_count = 0

        self._icon: Optional[pystray.Icon] = None
        self._lock = threading.Lock()

    def run(self) -> None:
        self._icon = pystray.Icon(
            name="presence_agent",
            icon=self._build_icon_image(COLOR_IDLE),
            title="Presence Agent",
            menu=self._build_menu(),
        )
        self._icon.run()

    def stop(self) -> None:
        if self._icon is not None:
            self._icon.stop()

    def update_status(
        self,
        monitoring: Optional[bool] = None,
        camera_ok: Optional[bool] = None,
        detector_ok: Optional[bool] = None,
        last_presence: Optional[str] = None,
        alert_count: Optional[int] = None,
    ) -> None:
        with self._lock:
            if monitoring is not None:
                self._monitoring = monitoring
            if camera_ok is not None:
                self._camera_ok = camera_ok
            if detector_ok is not None:
                self._detector_ok = detector_ok
            if last_presence is not None:
                self._last_presence = last_presence
            if alert_count is not None:
                self._alert_count = alert_count

        self._refresh()

    def _refresh(self) -> None:
        if self._icon is None:
            return
        color = COLOR_MONITORING if self._monitoring else COLOR_IDLE
        self._icon.icon = self._build_icon_image(color)
        self._icon.menu = self._build_menu()
        self._icon.update_menu()

    def _build_icon_image(self, color: tuple[int, int, int]) -> Image.Image:
        size = 64
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        margin = 6
        draw.ellipse([margin, margin, size - margin, size - margin], fill=color)
        return img

    def _build_menu(self) -> pystray.Menu:
        status_camera = "OK" if self._camera_ok else "Indisponivel"
        status_detector = "OK" if self._detector_ok else "Indisponivel"
        status_presence = self._last_presence or "Nenhuma ainda"

        if self._monitoring:
            toggle_item = pystray.MenuItem(
                "Parar monitoramento", self._handle_stop
            )
        else:
            toggle_item = pystray.MenuItem(
                "Iniciar monitoramento", self._handle_start
            )

        return pystray.Menu(
            toggle_item,
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(f"Camera: {status_camera}", None, enabled=False),
            pystray.MenuItem(f"Detector: {status_detector}", None, enabled=False),
            pystray.MenuItem(f"Ultima presenca: {status_presence}", None, enabled=False),
            pystray.MenuItem(f"Alertas: {self._alert_count}", None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Sair", self._handle_exit),
        )

    def _handle_start(self, icon, item) -> None:
        self._on_start()

    def _handle_stop(self, icon, item) -> None:
        self._on_stop()

    def _handle_exit(self, icon, item) -> None:
        self._on_exit()
        self.stop()
