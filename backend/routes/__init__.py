"""API route modules."""

from .approaches import router as approaches_router
from .chat import router as chat_router
from .conversations import router as conversations_router
from .auto_mode import router as auto_mode_router
from .settings import router as settings_router
from .gapmap import router as gapmap_router
from .websocket import router as websocket_router

__all__ = [
    "approaches_router",
    "chat_router",
    "conversations_router",
    "auto_mode_router",
    "settings_router",
    "gapmap_router",
    "websocket_router",
]
