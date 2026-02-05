"""Daemon manager for Wingman."""

import logging
import os
import signal
import subprocess
import sys
import time

from wingman.config.paths import WingmanPaths

logger = logging.getLogger(__name__)


class DaemonManager:
    """
    Manages Wingman as a background daemon.

    On macOS, uses launchd for proper system integration.
    Falls back to PID file management on other platforms.
    """

    LAUNCHD_LABEL = "com.wingman.agent"

    def __init__(self, paths: WingmanPaths):
        self.paths = paths
        self._is_macos = sys.platform == "darwin"

    def start(self) -> None:
        """Start the daemon."""
        if self._is_macos:
            self._start_launchd()
        else:
            self._start_pidfile()

    def stop(self) -> None:
        """Stop the daemon."""
        if self._is_macos:
            self._stop_launchd()
        else:
            self._stop_pidfile()

    def restart(self) -> None:
        """Restart the daemon."""
        self.stop()
        time.sleep(1)
        self.start()

    def is_running(self) -> bool:
        """Check if the daemon is running."""
        if self._is_macos:
            return self._is_launchd_running()
        else:
            return self._is_pidfile_running()

    def get_pid(self) -> int | None:
        """Get the PID of the running daemon."""
        if self._is_macos:
            return self._get_launchd_pid()
        else:
            return self._get_pidfile_pid()

    def get_uptime(self) -> float | None:
        """Get daemon uptime in seconds."""
        pid = self.get_pid()
        if pid is None:
            return None

        try:
            # Use ps to get process start time
            result = subprocess.run(
                ["ps", "-o", "etime=", "-p", str(pid)],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                etime = result.stdout.strip()
                return self._parse_etime(etime)
        except Exception:
            pass

        return None

    def _parse_etime(self, etime: str) -> float:
        """Parse ps etime format to seconds."""
        # Format: [[DD-]HH:]MM:SS
        parts = etime.replace("-", ":").split(":")
        parts = [int(p) for p in parts]

        if len(parts) == 2:
            # MM:SS
            return parts[0] * 60 + parts[1]
        elif len(parts) == 3:
            # HH:MM:SS
            return parts[0] * 3600 + parts[1] * 60 + parts[2]
        elif len(parts) == 4:
            # DD:HH:MM:SS
            return parts[0] * 86400 + parts[1] * 3600 + parts[2] * 60 + parts[3]

        return 0

    # ========== launchd implementation (macOS) ==========

    def _get_plist_content(self) -> str:
        """Generate launchd plist content."""
        python_path = sys.executable
        log_file = self.paths.log_dir / "agent.log"
        error_file = self.paths.log_dir / "error.log"

        return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{self.LAUNCHD_LABEL}</string>

    <key>ProgramArguments</key>
    <array>
        <string>{python_path}</string>
        <string>-m</string>
        <string>wingman.core.agent</string>
    </array>

    <key>RunAtLoad</key>
    <false/>

    <key>KeepAlive</key>
    <dict>
        <key>SuccessfulExit</key>
        <false/>
    </dict>

    <key>StandardOutPath</key>
    <string>{log_file}</string>

    <key>StandardErrorPath</key>
    <string>{error_file}</string>

    <key>WorkingDirectory</key>
    <string>{self.paths.config_dir}</string>

    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin</string>
    </dict>
</dict>
</plist>
"""

    def _start_launchd(self) -> None:
        """Start using launchd."""
        plist_path = self.paths.launchd_plist

        # Ensure log directory exists
        self.paths.log_dir.mkdir(parents=True, exist_ok=True)

        # Write plist file
        plist_path.parent.mkdir(parents=True, exist_ok=True)
        plist_path.write_text(self._get_plist_content())

        # Load and start the agent
        subprocess.run(
            ["launchctl", "load", str(plist_path)],
            check=True
        )
        subprocess.run(
            ["launchctl", "start", self.LAUNCHD_LABEL],
            check=True
        )

        logger.info(f"Daemon started via launchd: {self.LAUNCHD_LABEL}")

    def _stop_launchd(self) -> None:
        """Stop using launchd."""
        plist_path = self.paths.launchd_plist

        # Stop the agent
        subprocess.run(
            ["launchctl", "stop", self.LAUNCHD_LABEL],
            capture_output=True
        )

        # Unload the plist
        if plist_path.exists():
            subprocess.run(
                ["launchctl", "unload", str(plist_path)],
                capture_output=True
            )

        logger.info(f"Daemon stopped: {self.LAUNCHD_LABEL}")

    def _is_launchd_running(self) -> bool:
        """Check if launchd agent is running."""
        result = subprocess.run(
            ["launchctl", "list", self.LAUNCHD_LABEL],
            capture_output=True,
            text=True
        )
        return result.returncode == 0

    def _get_launchd_pid(self) -> int | None:
        """Get PID from launchd."""
        result = subprocess.run(
            ["launchctl", "list", self.LAUNCHD_LABEL],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            return None

        # Parse output: PID\tStatus\tLabel
        parts = result.stdout.strip().split("\t")
        if len(parts) >= 1 and parts[0] != "-":
            try:
                return int(parts[0])
            except ValueError:
                pass

        return None

    # ========== PID file implementation (fallback) ==========

    def _start_pidfile(self) -> None:
        """Start using PID file (non-macOS fallback)."""
        pid_file = self.paths.pid_file

        # Check if already running
        if self._is_pidfile_running():
            raise RuntimeError("Daemon is already running")

        # Fork and run in background
        python_path = sys.executable

        # Start as subprocess
        process = subprocess.Popen(
            [python_path, "-m", "wingman.core.agent"],
            stdout=open(self.paths.log_dir / "agent.log", "a"),
            stderr=open(self.paths.log_dir / "error.log", "a"),
            cwd=str(self.paths.config_dir),
            start_new_session=True,
        )

        # Write PID file
        pid_file.parent.mkdir(parents=True, exist_ok=True)
        pid_file.write_text(str(process.pid))

        logger.info(f"Daemon started with PID: {process.pid}")

    def _stop_pidfile(self) -> None:
        """Stop using PID file."""
        pid_file = self.paths.pid_file
        pid = self._get_pidfile_pid()

        if pid is None:
            return

        # Send SIGTERM
        try:
            os.kill(pid, signal.SIGTERM)

            # Wait for process to exit
            for _ in range(50):  # 5 seconds
                time.sleep(0.1)
                try:
                    os.kill(pid, 0)  # Check if still running
                except ProcessLookupError:
                    break
            else:
                # Force kill if still running
                os.kill(pid, signal.SIGKILL)

        except ProcessLookupError:
            pass  # Process already exited
        except Exception as e:
            logger.error(f"Error stopping daemon: {e}")

        # Remove PID file
        if pid_file.exists():
            pid_file.unlink()

        logger.info("Daemon stopped")

    def _is_pidfile_running(self) -> bool:
        """Check if daemon is running via PID file."""
        pid = self._get_pidfile_pid()
        if pid is None:
            return False

        try:
            os.kill(pid, 0)  # Check if process exists
            return True
        except ProcessLookupError:
            # Process doesn't exist, clean up stale PID file
            self.paths.pid_file.unlink(missing_ok=True)
            return False

    def _get_pidfile_pid(self) -> int | None:
        """Get PID from PID file."""
        pid_file = self.paths.pid_file
        if not pid_file.exists():
            return None

        try:
            return int(pid_file.read_text().strip())
        except (ValueError, FileNotFoundError):
            return None

    def uninstall(self) -> None:
        """Fully uninstall the daemon."""
        self.stop()

        # Remove launchd plist
        if self._is_macos and self.paths.launchd_plist.exists():
            self.paths.launchd_plist.unlink()

        # Remove PID file
        self.paths.pid_file.unlink(missing_ok=True)

        logger.info("Daemon uninstalled")
