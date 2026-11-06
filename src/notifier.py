"""
NotificationService

Envia notificacoes para o celular via Apprise (ntfy, Telegram,
Gotify, Discord, email etc, dependendo das URLs configuradas) e
aplica um cooldown para nao inundar o usuario de alertas repetidos.

Nao sabe nada sobre camera, detector ou filtro temporal. Recebe
apenas um pedido de "notificar agora" e decide se realmente envia
com base no cooldown.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import List, Optional

import apprise

logger = logging.getLogger("x9.notifier")


class NotificationService:
    def __init__(
        self,
        urls: List[str],
        cooldown_seconds: int = 600,
        title: str = "X9",
        message: str = "Presenca detectada no computador",
    ) -> None:
        self._cooldown_seconds = cooldown_seconds
        self._title = title
        self._message = message
        self._last_sent_at: Optional[float] = None
        self._lock = threading.Lock()

        self._apprise = apprise.Apprise()
        for url in urls:
            if not self._apprise.add(url):
                logger.warning("URL de notificacao invalida ou nao suportada: %s", url)

    def notify(self, extra_info: str = "", force: bool = False) -> bool:
        """Envia a notificacao se o cooldown ja tiver expirado.

        force=True ignora o cooldown: usado quando o PC foi bloqueado, um
        evento que o dono sempre precisa saber.
        Retorna True se enviou, False se ainda estava em cooldown.
        """
        with self._lock:
            now = time.time()
            if self._last_sent_at is not None and not force:
                elapsed = now - self._last_sent_at
                if elapsed < self._cooldown_seconds:
                    remaining = self._cooldown_seconds - elapsed
                    logger.info(
                        "Notificacao suprimida por cooldown, faltam %.0fs", remaining
                    )
                    return False

            body = self._message if not extra_info else f"{self._message} ({extra_info})"
            sent = self._apprise.notify(title=self._title, body=body)
            if sent:
                self._last_sent_at = now
                logger.info("Notificacao enviada")
            else:
                logger.error("Falha ao enviar notificacao para todas as URLs configuradas")
            return sent

    def rearm(self) -> bool:
        """Zera o cooldown para que o proximo alerta saia na hora.

        Chamado quando a ausencia da pessoa e confirmada: o cooldown existe
        para nao repetir alerta enquanto alguem continua sentado, e nao para
        engolir a chegada seguinte. Retorna True se havia cooldown ativo.
        """
        with self._lock:
            estava_armado = self._last_sent_at is not None
            self._last_sent_at = None
        if estava_armado:
            logger.info("Ausencia confirmada, cooldown liberado para o proximo alerta")
        return estava_armado

    def seconds_until_ready(self) -> float:
        """Quantos segundos faltam para o cooldown liberar um novo alerta."""
        if self._last_sent_at is None:
            return 0.0
        elapsed = time.time() - self._last_sent_at
        return max(0.0, self._cooldown_seconds - elapsed)
