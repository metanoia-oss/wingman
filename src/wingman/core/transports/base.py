"""Base transport abstraction for multi-platform messaging."""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Coroutine, Optional

logger = logging.getLogger(__name__)


class Platform(Enum):
    """Supported messaging platforms."""
    WHATSAPP = "whatsapp"
    IMESSAGE = "imessage"


@dataclass
class MessageEvent:
    """Unified message structure across all platforms."""
    # Core message data
    chat_id: str
    sender_id: str
    text: str
    timestamp: float

    # Platform info
    platform: Platform

    # Sender info
    sender_name: Optional[str] = None

    # Message type flags
    is_group: bool = False
    is_self: bool = False

    # Platform-specific data
    raw_data: dict = field(default_factory=dict)

    # Reply context (if replying to a message)
    quoted_message: Optional[dict] = None


# Type alias for message handler callback
MessageHandler = Callable[[MessageEvent], Coroutine[Any, Any, None]]


class BaseTransport(ABC):
    """Abstract base class for message transports."""

    def __init__(self):
        self._message_handler: Optional[MessageHandler] = None
        self._running = False

    @property
    @abstractmethod
    def platform(self) -> Platform:
        """Return the platform this transport handles."""
        pass

    def set_message_handler(self, handler: MessageHandler) -> None:
        """Set the callback for incoming messages."""
        self._message_handler = handler
        logger.debug(f"{self.platform.value}: Message handler registered")

    async def _dispatch_message(self, event: MessageEvent) -> None:
        """Dispatch a message event to the registered handler."""
        if self._message_handler:
            try:
                await self._message_handler(event)
            except Exception as e:
                logger.error(f"{self.platform.value}: Error in message handler: {e}")
        else:
            logger.warning(f"{self.platform.value}: No message handler registered")

    @abstractmethod
    async def start(self) -> None:
        """Start the transport and begin listening for messages."""
        pass

    @abstractmethod
    async def stop(self) -> None:
        """Stop the transport gracefully."""
        pass

    @abstractmethod
    async def send_message(self, chat_id: str, text: str) -> bool:
        """
        Send a message to the specified chat.

        Args:
            chat_id: The chat/conversation identifier
            text: The message text to send

        Returns:
            True if send was successful, False otherwise
        """
        pass

    @property
    def is_running(self) -> bool:
        """Check if the transport is currently running."""
        return self._running
