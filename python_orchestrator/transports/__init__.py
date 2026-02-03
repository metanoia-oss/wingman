"""Transport abstraction layer for multi-platform messaging."""

from .base import Platform, MessageEvent, BaseTransport, MessageHandler
from .whatsapp import WhatsAppTransport
from .imessage import IMessageTransport

__all__ = [
    "Platform",
    "MessageEvent",
    "BaseTransport",
    "MessageHandler",
    "WhatsAppTransport",
    "IMessageTransport",
]
