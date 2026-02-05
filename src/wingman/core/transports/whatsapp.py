"""WhatsApp transport implementation wrapping Node.js IPC."""

import logging
import time
from collections.abc import Callable, Coroutine
from pathlib import Path

from ..ipc_handler import IPCHandler
from ..process_manager import NodeProcessManager
from .base import BaseTransport, MessageEvent, Platform

logger = logging.getLogger(__name__)


class WhatsAppTransport(BaseTransport):
    """
    WhatsApp transport using Baileys via Node.js subprocess.
    Wraps the existing Node.js IPC communication.
    """

    def __init__(self, node_dir: Path, auth_state_dir: Path | None = None):
        super().__init__()
        self._node_manager = NodeProcessManager(node_dir, auth_state_dir)
        self._ipc: IPCHandler | None = None
        self._self_id: str | None = None

        # Callbacks for WhatsApp-specific events
        self._on_connected: Callable[[str], Coroutine] | None = None
        self._on_disconnected: Callable[[], Coroutine] | None = None
        self._on_qr_code: Callable[[], Coroutine] | None = None

    @property
    def platform(self) -> Platform:
        return Platform.WHATSAPP

    @property
    def self_id(self) -> str | None:
        """Get the connected WhatsApp user ID."""
        return self._self_id

    def set_connected_handler(self, handler: Callable[[str], Coroutine]) -> None:
        """Set callback for when WhatsApp connects."""
        self._on_connected = handler

    def set_disconnected_handler(self, handler: Callable[[], Coroutine]) -> None:
        """Set callback for when WhatsApp disconnects."""
        self._on_disconnected = handler

    def set_qr_code_handler(self, handler: Callable[[], Coroutine]) -> None:
        """Set callback for QR code events."""
        self._on_qr_code = handler

    async def start(self) -> None:
        """Start the WhatsApp transport."""
        logger.info("Starting WhatsApp transport...")
        self._running = True

        # Start Node.js subprocess
        self._ipc = await self._node_manager.start()

        # Register IPC handlers
        self._register_ipc_handlers()

        logger.info("WhatsApp transport started")

        # Run the IPC loop (blocks until stopped)
        try:
            await self._ipc.start()
        except Exception as e:
            logger.error(f"WhatsApp IPC loop error: {e}")
            self._running = False
            raise

    def _register_ipc_handlers(self) -> None:
        """Register handlers for Node.js IPC events."""
        if not self._ipc:
            return

        async def on_message(data: dict) -> None:
            """Handle incoming WhatsApp message."""
            event = self._convert_to_event(data)
            await self._dispatch_message(event)

        async def on_connected(data: dict) -> None:
            """Handle WhatsApp connection."""
            user = data.get('user', {})
            user_id = user.get('id', '')
            self._self_id = user_id
            logger.info(f"WhatsApp connected: {user_id}")
            if self._on_connected:
                await self._on_connected(user_id)

        async def on_disconnected(data: dict) -> None:
            """Handle WhatsApp disconnection."""
            logger.warning(f"WhatsApp disconnected: {data}")
            if self._on_disconnected:
                await self._on_disconnected()

        async def on_qr_code(data: dict) -> None:
            """Handle QR code event."""
            logger.info("QR code received - check terminal")
            if self._on_qr_code:
                await self._on_qr_code()

        async def on_error(data: dict) -> None:
            """Handle Node.js error."""
            logger.error(f"WhatsApp error: {data.get('message', 'Unknown error')}")

        async def on_logged_out(data: dict) -> None:
            """Handle logout event."""
            logger.error("Logged out from WhatsApp")
            if self._on_disconnected:
                await self._on_disconnected()

        async def on_send_result(data: dict) -> None:
            """Handle send result."""
            success = data.get('success', False)
            jid = data.get('jid', '')
            if success:
                logger.debug(f"Message sent to {jid}")
            else:
                logger.error(f"Failed to send message to {jid}")

        async def on_starting(data: dict) -> None:
            logger.info("Node.js starting...")

        async def on_pong(data: dict) -> None:
            logger.debug("Pong received")

        # Register all handlers
        self._ipc.register_handler('message', on_message)
        self._ipc.register_handler('connected', on_connected)
        self._ipc.register_handler('disconnected', on_disconnected)
        self._ipc.register_handler('qr_code', on_qr_code)
        self._ipc.register_handler('error', on_error)
        self._ipc.register_handler('logged_out', on_logged_out)
        self._ipc.register_handler('send_result', on_send_result)
        self._ipc.register_handler('starting', on_starting)
        self._ipc.register_handler('pong', on_pong)

    def _convert_to_event(self, data: dict) -> MessageEvent:
        """Convert IPC message data to MessageEvent."""
        return MessageEvent(
            chat_id=data.get('chatId', ''),
            sender_id=data.get('senderId', ''),
            text=data.get('text', ''),
            timestamp=data.get('timestamp', time.time()),
            platform=Platform.WHATSAPP,
            sender_name=data.get('senderName'),
            is_group=data.get('isGroup', False),
            is_self=data.get('isSelf', False),
            raw_data=data,
            quoted_message=data.get('quotedMessage'),
        )

    async def stop(self) -> None:
        """Stop the WhatsApp transport."""
        logger.info("Stopping WhatsApp transport...")
        self._running = False

        if self._ipc:
            self._ipc.stop()

        await self._node_manager.stop()
        self._ipc = None

        logger.info("WhatsApp transport stopped")

    async def send_message(self, chat_id: str, text: str) -> bool:
        """Send a WhatsApp message."""
        if not self._ipc:
            logger.error("Cannot send message: IPC not connected")
            return False

        try:
            await self._ipc.send_message(chat_id, text)
            return True
        except Exception as e:
            logger.error(f"Failed to send WhatsApp message: {e}")
            return False
