"""Unix domain socket RPC client for the console."""

import json
import socket
import uuid
from pathlib import Path
from typing import Any

DELIMITER = b"\0"


class RPCError(Exception):
    """Error communicating with the daemon."""

    pass


class RPCClient:
    """
    Synchronous RPC client for the console REPL.

    Connects to the daemon's Unix domain socket.
    """

    def __init__(self, socket_path: Path, timeout: float = 5.0) -> None:
        self._socket_path = socket_path
        self._timeout = timeout

    @property
    def available(self) -> bool:
        """Check if the daemon socket exists."""
        return self._socket_path.exists()

    def call(self, method: str, params: dict | None = None) -> Any:
        """
        Make an RPC call to the daemon.

        Args:
            method: RPC method name
            params: Method parameters

        Returns:
            The result from the daemon

        Raises:
            RPCError: If communication fails or daemon returns an error
        """
        if not self.available:
            raise RPCError("Daemon is not running (no socket found)")

        request = {
            "id": str(uuid.uuid4()),
            "method": method,
            "params": params or {},
        }

        try:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.settimeout(self._timeout)
            sock.connect(str(self._socket_path))

            # Send request
            sock.sendall(json.dumps(request).encode("utf-8") + DELIMITER)

            # Receive response
            buffer = b""
            while DELIMITER not in buffer:
                chunk = sock.recv(4096)
                if not chunk:
                    raise RPCError("Connection closed by daemon")
                buffer += chunk

            response_data = buffer.split(DELIMITER, 1)[0]
            response = json.loads(response_data.decode("utf-8"))

            sock.close()

            if response.get("error"):
                raise RPCError(response["error"])

            return response.get("result")

        except socket.timeout:
            raise RPCError("Daemon did not respond in time")
        except ConnectionRefusedError:
            raise RPCError("Daemon refused connection (may have crashed)")
        except FileNotFoundError:
            raise RPCError("Daemon is not running (socket not found)")
        except json.JSONDecodeError:
            raise RPCError("Invalid response from daemon")

    def ping(self) -> bool:
        """Check if daemon is responsive."""
        try:
            result = self.call("ping")
            return result.get("pong", False)
        except RPCError:
            return False

    def get_status(self) -> dict:
        """Get daemon status."""
        return self.call("get_status")

    def send_message(self, jid: str, text: str, platform: str = "whatsapp") -> dict:
        """Send a message via the daemon."""
        return self.call("send_message", {"jid": jid, "text": text, "platform": platform})

    def pause(self, duration: float | None = None) -> dict:
        """Pause message processing."""
        return self.call("pause", {"duration": duration})

    def resume(self) -> dict:
        """Resume message processing."""
        return self.call("resume")

    def list_active_chats(self, limit: int = 20) -> dict:
        """List recent active chats."""
        return self.call("list_active_chats", {"limit": limit})
