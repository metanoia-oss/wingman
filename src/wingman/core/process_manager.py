"""Node.js subprocess management."""

import asyncio
import logging
from pathlib import Path
from typing import Optional

from .ipc_handler import IPCHandler, IPCCommand

logger = logging.getLogger(__name__)


class NodeProcessManager:
    """Manages the Node.js listener subprocess."""

    def __init__(self, node_dir: Path, auth_state_dir: Optional[Path] = None):
        self.node_dir = node_dir
        self.auth_state_dir = auth_state_dir
        self.process: Optional[asyncio.subprocess.Process] = None
        self.ipc: Optional[IPCHandler] = None
        self._stderr_task: Optional[asyncio.Task] = None

    async def start(self) -> IPCHandler:
        """Start the Node.js subprocess and return IPC handler."""
        node_script = self.node_dir / "dist" / "index.js"

        if not node_script.exists():
            raise FileNotFoundError(
                f"Node.js script not found: {node_script}\n"
                "Run 'npm run build' in node_listener directory first."
            )

        logger.info(f"Starting Node.js subprocess: {node_script}")

        # Build environment with optional auth state directory
        env = None
        if self.auth_state_dir:
            import os
            env = os.environ.copy()
            env["AUTH_STATE_DIR"] = str(self.auth_state_dir)

        self.process = await asyncio.create_subprocess_exec(
            "node",
            str(node_script),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(self.node_dir),
            env=env
        )

        if not self.process.stdin or not self.process.stdout:
            raise RuntimeError("Failed to create subprocess pipes")

        # Create IPC handler
        self.ipc = IPCHandler(
            stdin=self.process.stdin,
            stdout=self.process.stdout
        )

        # Start stderr reader for logging
        self._stderr_task = asyncio.create_task(self._read_stderr())

        logger.info(f"Node.js subprocess started (PID: {self.process.pid})")
        return self.ipc

    async def _read_stderr(self) -> None:
        """Read and log Node.js stderr output."""
        if not self.process or not self.process.stderr:
            return

        while True:
            try:
                line = await self.process.stderr.readline()
                if not line:
                    break

                # Node logs JSON to stderr
                log_line = line.decode('utf-8').strip()
                if log_line:
                    # Check if it's a QR code line (contains block characters)
                    if any(c in log_line for c in ['▄', '█', '▀', '=']):
                        # Print QR directly to stderr for user to see
                        print(log_line, flush=True)
                    else:
                        logger.debug(f"[Node] {log_line}")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error reading stderr: {e}")
                break

    async def stop(self) -> None:
        """Stop the Node.js subprocess gracefully."""
        if not self.process:
            return

        logger.info("Stopping Node.js subprocess...")

        # Cancel stderr reader
        if self._stderr_task:
            self._stderr_task.cancel()
            try:
                await self._stderr_task
            except asyncio.CancelledError:
                pass

        # Try graceful shutdown first
        if self.ipc:
            try:
                await asyncio.wait_for(
                    self.ipc.send_command(IPCCommand(action="shutdown")),
                    timeout=2.0
                )
            except Exception as e:
                logger.warning(f"Failed to send shutdown command: {e}")

        # Wait for process to exit
        try:
            await asyncio.wait_for(self.process.wait(), timeout=5.0)
            logger.info("Node.js subprocess exited gracefully")
        except asyncio.TimeoutError:
            logger.warning("Node.js subprocess did not exit, terminating...")
            self.process.terminate()
            try:
                await asyncio.wait_for(self.process.wait(), timeout=2.0)
            except asyncio.TimeoutError:
                logger.error("Node.js subprocess did not terminate, killing...")
                self.process.kill()
                await self.process.wait()

        self.process = None
        self.ipc = None

    @property
    def is_running(self) -> bool:
        """Check if the subprocess is running."""
        return self.process is not None and self.process.returncode is None
