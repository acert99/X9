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
from typing import Callable, List, Optional, Tuple

import pystray
from PIL import Image, ImageDraw

from paths import resource_path

logger = logging.getLogger("x9.tray")

COLOR_IDLE = (120, 120, 120)
COLOR_MONITORING = (46, 160, 67)
COLOR_ALERT = (200, 60, 60)


class TrayInterface:
    def __init__(
        self,
        on_start: Callable[[], None],
        on_stop: Callable[[], None],
        on_exit: Callable[[], None],
        list_cameras: Callable[[], List[Tuple[int, str]]] = lambda: [],
        on_select_camera: Callable[[int], None] = lambda index: None,
        current_camera: Callable[[], int] = lambda: 0,
    ) -> None:
        self._list_cameras = list_cameras
        self._on_select_camera = on_select_camera
        self._current_camera = current_camera
        self._cameras: List[Tuple[int, str]] = []
        self._on_start = on_start
        self._on_stop = on_stop
        self._on_exit = on_exit

        self._monitoring = False
        self._camera_ok = False
        self._detector_ok = False
        self._last_presence: Optional[str] = None
        self._alert_count = 0

        self._base_icon = self._load_base_icon()
        self._icon: Optional[pystray.Icon] = None
        self._lock = threading.Lock()

    def run(self) -> None:
        self._cameras = self._list_cameras()
        self._icon = pystray.Icon(
            name="x9",
            icon=self._build_icon_image(COLOR_IDLE),
            title="X9",
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

    @staticmethod
    def _load_base_icon() -> Optional[Image.Image]:
        try:
            return Image.open(resource_path("assets/icon.png")).convert("RGBA").resize(
                (64, 64), Image.LANCZOS
            )
        except (OSError, ValueError):
            logger.warning("assets/icon.png nao encontrado, usando icone simples")
            return None

    def _build_icon_image(self, color: tuple[int, int, int]) -> Image.Image:
        size = 64
        if self._base_icon is None:
            img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            margin = 6
            draw.ellipse([margin, margin, size - margin, size - margin], fill=color)
            return img

        # Detetive com uma bolinha de status no canto: verde vigiando,
        # cinza parado. Borda escura para a bolinha aparecer em qualquer
        # cor de barra de tarefas.
        img = self._base_icon.copy()
        draw = ImageDraw.Draw(img)
        dot = 26
        draw.ellipse(
            [size - dot - 1, size - dot - 1, size - 1, size - 1],
            fill=color,
            outline=(20, 20, 20),
            width=4,
        )
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
            pystray.MenuItem("Camera", self._build_camera_menu()),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(f"Camera: {status_camera}", None, enabled=False),
            pystray.MenuItem(f"Detector: {status_detector}", None, enabled=False),
            pystray.MenuItem(f"Ultima presenca: {status_presence}", None, enabled=False),
            pystray.MenuItem(f"Alertas: {self._alert_count}", None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Sair", self._handle_exit),
        )

    def _build_camera_menu(self) -> pystray.Menu:
        def item_for(index: int, name: str) -> pystray.MenuItem:
            return pystray.MenuItem(
                name,
                lambda icon, item: self._on_select_camera(index),
                checked=lambda item: self._current_camera() == index,
                radio=True,
            )

        items = [item_for(i, n) for i, n in self._cameras]
        if not items:
            items = [pystray.MenuItem("Nenhuma camera encontrada", None, enabled=False)]
        items += [
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Procurar cameras de novo", self._handle_rescan),
        ]
        return pystray.Menu(*items)

    def _handle_rescan(self, icon, item) -> None:
        self._cameras = self._list_cameras()
        self._refresh()

    def _handle_start(self, icon, item) -> None:
        self._on_start()

    def _handle_stop(self, icon, item) -> None:
        self._on_stop()

    def _handle_exit(self, icon, item) -> None:
        self._on_exit()
        self.stop()
