"""Transport abstraction layer for multi-platform messaging."""

from .base import BaseTransport, MessageEvent, MessageHandler, Platform
from .imessage import IMessageTransport
from .whatsapp import WhatsAppTransport

__all__ = [
    "Platform",
    "MessageEvent",
    "BaseTransport",
    "MessageHandler",
    "WhatsAppTransport",
    "IMessageTransport",
]
