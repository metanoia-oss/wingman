"""Tests for RPC client and server."""

import json
import os
import socket
import tempfile
import threading
from pathlib import Path

from wingman.core.rpc_client import RPCClient, RPCError


def _short_sock_path():
    """Create a short socket path to avoid AF_UNIX length limits on macOS."""
    fd, path = tempfile.mkstemp(suffix=".sock", dir="/tmp")
    os.close(fd)
    os.unlink(path)
    return Path(path)


class TestRPCClient:
    def test_not_available(self, tmp_path):
        client = RPCClient(tmp_path / "nonexistent.sock")
        assert client.available is False

    def test_ping_no_daemon(self, tmp_path):
        client = RPCClient(tmp_path / "nonexistent.sock")
        assert client.ping() is False

    def test_call_no_socket(self, tmp_path):
        client = RPCClient(tmp_path / "nonexistent.sock")
        try:
            client.call("ping")
            assert False, "Should have raised RPCError"
        except RPCError:
            pass

    def test_call_with_mock_server(self):
        """Test RPC client against a simple mock server."""
        sock_path = _short_sock_path()

        # Create a simple mock server
        server_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            server_sock.bind(str(sock_path))
            server_sock.listen(1)
            server_sock.settimeout(5)

            response_sent = threading.Event()

            def mock_server():
                conn, _ = server_sock.accept()
                data = b""
                while b"\0" not in data:
                    data += conn.recv(4096)

                # Parse request
                request = json.loads(data.split(b"\0")[0])
                response = {
                    "id": request["id"],
                    "result": {"pong": True},
                    "error": None,
                }
                conn.sendall(json.dumps(response).encode() + b"\0")
                response_sent.set()
                conn.close()

            thread = threading.Thread(target=mock_server, daemon=True)
            thread.start()

            client = RPCClient(sock_path, timeout=5.0)
            assert client.available is True

            result = client.call("ping")
            assert result["pong"] is True

            response_sent.wait(timeout=5)
        finally:
            server_sock.close()
            sock_path.unlink(missing_ok=True)

    def test_call_server_error(self):
        """Test RPC client handles server error responses."""
        sock_path = _short_sock_path()

        server_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            server_sock.bind(str(sock_path))
            server_sock.listen(1)
            server_sock.settimeout(5)

            def mock_server():
                conn, _ = server_sock.accept()
                data = b""
                while b"\0" not in data:
                    data += conn.recv(4096)

                request = json.loads(data.split(b"\0")[0])
                response = {
                    "id": request["id"],
                    "result": None,
                    "error": "Test error message",
                }
                conn.sendall(json.dumps(response).encode() + b"\0")
                conn.close()

            thread = threading.Thread(target=mock_server, daemon=True)
            thread.start()

            client = RPCClient(sock_path, timeout=5.0)
            try:
                client.call("bad_method")
                assert False, "Should have raised RPCError"
            except RPCError as e:
                assert "Test error message" in str(e)
        finally:
            server_sock.close()
            sock_path.unlink(missing_ok=True)


class TestRPCClientMethods:
    def test_send_message_method_exists(self):
        client = RPCClient(Path("/tmp/test.sock"))
        assert hasattr(client, "send_message")
        assert hasattr(client, "pause")
        assert hasattr(client, "resume")
        assert hasattr(client, "get_status")
        assert hasattr(client, "list_active_chats")
