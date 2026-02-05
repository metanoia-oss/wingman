"""Unix domain socket RPC server for the daemon."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .agent import MultiTransportAgent

logger = logging.getLogger(__name__)

# NULL-delimited JSON protocol (matches existing IPC convention)
DELIMITER = b"\0"


class RPCServer:
    """
    Unix domain socket RPC server that runs inside the daemon.

    Provides methods for the console to communicate with the running agent.
    """

    def __init__(self, socket_path: Path, agent: MultiTransportAgent) -> None:
        self._socket_path = socket_path
        self._agent = agent
        self._server: asyncio.AbstractServer | None = None
        self._start_time = time.time()

    async def start(self) -> None:
        """Start the RPC server."""
        # Clean up stale socket
        if self._socket_path.exists():
            self._socket_path.unlink()

        self._socket_path.parent.mkdir(parents=True, exist_ok=True)

        self._server = await asyncio.start_unix_server(
            self._handle_client, path=str(self._socket_path)
        )

        # Set socket permissions to owner-only
        os.chmod(self._socket_path, 0o600)

        logger.info(f"RPC server listening on {self._socket_path}")

    async def stop(self) -> None:
        """Stop the RPC server."""
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            logger.info("RPC server stopped")

        if self._socket_path.exists():
            self._socket_path.unlink()

    async def _handle_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        """Handle a client connection."""
        try:
            buffer = b""
            while True:
                data = await reader.read(4096)
                if not data:
                    break

                buffer += data
                while DELIMITER in buffer:
                    message, buffer = buffer.split(DELIMITER, 1)
                    if message:
                        response = await self._process_request(message.decode("utf-8"))
                        writer.write(json.dumps(response).encode("utf-8") + DELIMITER)
                        await writer.drain()
        except (ConnectionResetError, BrokenPipeError):
            pass
        except Exception as e:
            logger.error(f"RPC client error: {e}")
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass

    async def _process_request(self, raw: str) -> dict[str, Any]:
        """Process a single RPC request and return the response."""
        try:
            request = json.loads(raw)
        except json.JSONDecodeError:
            return {"id": None, "result": None, "error": "Invalid JSON"}

        req_id = request.get("id")
        method = request.get("method", "")
        params = request.get("params", {})

        try:
            handler = getattr(self, f"_rpc_{method}", None)
            if handler is None:
                return {"id": req_id, "result": None, "error": f"Unknown method: {method}"}
            result = await handler(params)
            return {"id": req_id, "result": result, "error": None}
        except Exception as e:
            logger.error(f"RPC method error ({method}): {e}")
            return {"id": req_id, "result": None, "error": str(e)}

    # ========== RPC Methods ==========

    async def _rpc_ping(self, params: dict) -> dict:
        return {"pong": True, "uptime": time.time() - self._start_time}

    async def _rpc_get_status(self, params: dict) -> dict:
        transports = {}
        for platform, transport in self._agent.transports.items():
            transports[platform.value] = {"active": True}

        return {
            "running": True,
            "bot_name": self._agent.settings.bot_name,
            "model": self._agent.settings.openai_model,
            "uptime": time.time() - self._start_time,
            "transports": transports,
            "paused": getattr(self._agent.processor, "paused", False),
            "pause_until": getattr(self._agent.processor, "pause_until", None),
        }

    async def _rpc_send_message(self, params: dict) -> dict:
        jid = params.get("jid", "")
        text = params.get("text", "")
        platform = params.get("platform", "whatsapp")

        if not jid or not text:
            return {"success": False, "error": "jid and text required"}

        success = await self._agent._send_message(platform, jid, text)
        return {"success": success}

    async def _rpc_pause(self, params: dict) -> dict:
        duration = params.get("duration")
        processor = self._agent.processor

        processor.paused = True
        if duration:
            processor.pause_until = time.time() + duration
        else:
            processor.pause_until = None

        return {"paused": True, "until": processor.pause_until}

    async def _rpc_resume(self, params: dict) -> dict:
        processor = self._agent.processor
        processor.paused = False
        processor.pause_until = None
        return {"paused": False}

    async def _rpc_list_active_chats(self, params: dict) -> dict:
        limit = params.get("limit", 20)
        chats = self._agent.processor.store.get_recent_chats(limit)
        return {"chats": chats}
