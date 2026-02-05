"""iMessage transport implementation."""

import asyncio
import logging
from pathlib import Path

from ..base import BaseTransport, MessageEvent, Platform
from .db_listener import IMessageData, IMessageDBListener
from .sender import IMessageSender

logger = logging.getLogger(__name__)


class IMessageTransport(BaseTransport):
    """
    iMessage transport using chat.db polling and AppleScript sending.

    Requirements:
    - macOS only
    - Full Disk Access permission for the Python process
    - Messages.app configured with iMessage account
    """

    def __init__(
        self,
        db_path: Path | None = None,
        poll_interval: float = 2.0,
    ):
        super().__init__()
        self._listener = IMessageDBListener(
            db_path=db_path,
            poll_interval=poll_interval,
        )
        self._sender = IMessageSender()
        self._listener_task: asyncio.Task | None = None

    @property
    def platform(self) -> Platform:
        return Platform.IMESSAGE

    async def start(self) -> None:
        """Start the iMessage transport."""
        logger.info("Starting iMessage transport...")
        self._running = True

        # Set up message callback
        self._listener.set_message_callback(self._on_message)

        # Start listener in background task
        self._listener_task = asyncio.create_task(self._listener.start())

        logger.info("iMessage transport started")

    async def _on_message(self, msg: IMessageData) -> None:
        """Handle incoming iMessage from the database listener."""
        # Skip our own messages
        if msg.is_from_me:
            logger.debug(f"Skipping self message: {msg.text[:30]}...")
            return

        # Convert to MessageEvent
        event = MessageEvent(
            chat_id=msg.chat_id or f"imessage:{msg.handle_id}",
            sender_id=f"imessage:{msg.handle_id}",
            text=msg.text,
            timestamp=msg.timestamp,
            platform=Platform.IMESSAGE,
            sender_name=msg.chat_name if msg.is_group else None,
            is_group=msg.is_group,
            is_self=msg.is_from_me,
            raw_data={
                'rowid': msg.rowid,
                'handle_id': msg.handle_id,
                'chat_id': msg.chat_id,
                'chat_name': msg.chat_name,
                'is_group': msg.is_group,
            },
        )

        logger.info(
            f"iMessage received: from={msg.handle_id}, "
            f"group={msg.is_group}, text={msg.text[:50]}..."
        )

        await self._dispatch_message(event)

    async def stop(self) -> None:
        """Stop the iMessage transport."""
        logger.info("Stopping iMessage transport...")
        self._running = False

        # Stop the listener
        await self._listener.stop()

        # Cancel listener task
        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass

        logger.info("iMessage transport stopped")

    async def send_message(self, chat_id: str, text: str) -> bool:
        """Send an iMessage."""
        # Parse chat_id to determine if group or individual
        # Format: "imessage:+1234567890" or "chat123456789"

        if chat_id.startswith("imessage:"):
            # Direct message - extract phone/email
            recipient = chat_id.replace("imessage:", "")
            return await self._sender.send_message(
                recipient=recipient,
                text=text,
                is_group=False,
            )
        else:
            # Group chat - use chat_id directly
            # Extract handle from raw_data if available
            return await self._sender.send_message(
                recipient=chat_id,
                text=text,
                is_group=True,
                chat_id=chat_id,
            )

    async def check_availability(self) -> bool:
        """Check if iMessage is available on this system."""
        # Check if chat.db exists
        if not self._listener._db_path.exists():
            logger.warning("iMessage database not found")
            return False

        # Check if Messages.app is accessible
        if not await self._sender.check_messages_app():
            logger.warning("Messages.app not accessible")
            return False

        return True
