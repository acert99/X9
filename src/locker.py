"""
ScreenLocker

Bloqueia a sessao do Windows, o mesmo efeito de apertar Win+L: a tela
volta para o login e so sai de la com a senha (ou PIN) do usuario.

Usa a API LockWorkStation da user32.dll em vez de simular o atalho de
teclado. Simular Win+L e menos confiavel (o Windows pode bloquear
teclas injetadas, e o atalho pode estar desativado por politica), e a
API faz exatamente a mesma coisa.

Nao sabe nada sobre camera, detector ou notificacao.
"""

from __future__ import annotations

import logging
import sys

logger = logging.getLogger("x9.locker")


def lock_workstation() -> bool:
    """Bloqueia a sessao atual. Retorna True se o Windows aceitou o pedido."""
    if sys.platform != "win32":
        logger.warning("Bloqueio de tela so funciona no Windows")
        return False

    import ctypes

    ok = bool(ctypes.windll.user32.LockWorkStation())
    if ok:
        logger.info("Sessao do Windows bloqueada")
    else:
        logger.error("Windows recusou o pedido de bloqueio de sessao")
    return ok
