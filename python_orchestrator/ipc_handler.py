"""IPC Handler for communication with Node.js subprocess."""

import json
import asyncio
import logging
from typing import Any, Callable, Coroutine, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

NULL_CHAR = '\0'


@dataclass
class IPCMessage:
    """Message received from Node.js."""
    type: str
    data: Optional[dict] = None


@dataclass
class IPCCommand:
    """Command to send to Node.js."""
    action: str
    payload: Optional[dict] = None


class IPCHandler:
    """Handles JSON IPC communication with Node.js subprocess."""

    def __init__(
        self,
        stdin: asyncio.StreamWriter,
        stdout: asyncio.StreamReader
    ):
        self.stdin = stdin
        self.stdout = stdout
        self._buffer = ""
        self._handlers: dict[str, Callable[[dict], Coroutine]] = {}
        self._running = False

    def register_handler(
        self,
        message_type: str,
        handler: Callable[[dict], Coroutine]
    ) -> None:
        """Register a handler for a specific message type."""
        self._handlers[message_type] = handler
        logger.debug(f"Registered handler for: {message_type}")

    async def send_command(self, command: IPCCommand) -> None:
        """Send a command to Node.js."""
        try:
            message = {
                "action": command.action,
                **({"payload": command.payload} if command.payload else {})
            }
            json_str = json.dumps(message) + NULL_CHAR
            self.stdin.write(json_str.encode('utf-8'))
            await self.stdin.drain()
            logger.debug(f"Sent command: {command.action}")
        except Exception as e:
            logger.error(f"Failed to send command: {e}")
            raise

    async def send_message(self, jid: str, text: str, message_id: Optional[str] = None) -> None:
        """Convenience method to send a WhatsApp message."""
        await self.send_command(IPCCommand(
            action="send_message",
            payload={
                "jid": jid,
                "text": text,
                **({"messageId": message_id} if message_id else {})
            }
        ))

    async def _read_messages(self) -> None:
        """Read and process messages from Node.js stdout."""
        while self._running:
            try:
                chunk = await self.stdout.read(4096)
                if not chunk:
                    logger.warning("Node.js stdout closed")
                    break

                self._buffer += chunk.decode('utf-8')

                # Process all complete messages
                while NULL_CHAR in self._buffer:
                    null_idx = self._buffer.index(NULL_CHAR)
                    json_str = self._buffer[:null_idx]
                    self._buffer = self._buffer[null_idx + 1:]

                    if json_str.strip():
                        await self._process_message(json_str)

            except asyncio.CancelledError:
                logger.info("Message reader cancelled")
                break
            except Exception as e:
                logger.error(f"Error reading from stdout: {e}")
                await asyncio.sleep(0.1)

    async def _process_message(self, json_str: str) -> None:
        """Parse and dispatch a single message."""
        try:
            data = json.loads(json_str)
            message = IPCMessage(
                type=data.get("type", "unknown"),
                data=data.get("data")
            )

            handler = self._handlers.get(message.type)
            if handler:
                await handler(message.data or {})
            else:
                logger.debug(f"No handler for message type: {message.type}")

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}")
        except Exception as e:
            logger.error(f"Error processing message: {e}")

    async def start(self) -> None:
        """Start the IPC message loop."""
        self._running = True
        await self._read_messages()

    def stop(self) -> None:
        """Stop the IPC message loop."""
        self._running = False
