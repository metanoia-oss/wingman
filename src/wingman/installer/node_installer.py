"""Node.js listener installer."""

import logging
import shutil
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


class NodeInstaller:
    """
    Installs the Node.js WhatsApp listener.

    Handles:
    - Checking for Node.js/npm prerequisites
    - Copying bundled source to config directory
    - Running npm install and npm run build
    """

    # Minimum required versions
    MIN_NODE_VERSION = (18, 0, 0)
    MIN_NPM_VERSION = (9, 0, 0)

    def __init__(self, target_dir: Path):
        """
        Initialize the installer.

        Args:
            target_dir: Directory to install the node_listener to
        """
        self.target_dir = target_dir

    def check_prerequisites(self) -> tuple[bool, list[str]]:
        """
        Check if Node.js and npm are installed and meet version requirements.

        Returns:
            Tuple of (all_ok, list of issues)
        """
        issues = []

        # Check Node.js
        node_version = self._get_node_version()
        if node_version is None:
            issues.append("Node.js is not installed. Install from https://nodejs.org/")
        elif node_version < self.MIN_NODE_VERSION:
            version_str = ".".join(map(str, node_version))
            min_str = ".".join(map(str, self.MIN_NODE_VERSION))
            issues.append(f"Node.js {version_str} is too old. Minimum: {min_str}")

        # Check npm
        npm_version = self._get_npm_version()
        if npm_version is None:
            issues.append("npm is not installed")
        elif npm_version < self.MIN_NPM_VERSION:
            version_str = ".".join(map(str, npm_version))
            min_str = ".".join(map(str, self.MIN_NPM_VERSION))
            issues.append(f"npm {version_str} is too old. Minimum: {min_str}")

        return len(issues) == 0, issues

    def _get_node_version(self) -> tuple[int, ...] | None:
        """Get the installed Node.js version."""
        try:
            result = subprocess.run(
                ["node", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                # Parse version like "v20.10.0"
                version_str = result.stdout.strip().lstrip("v")
                parts = version_str.split(".")
                return tuple(int(p) for p in parts[:3])
        except (subprocess.SubprocessError, FileNotFoundError, ValueError):
            pass
        return None

    def _get_npm_version(self) -> tuple[int, ...] | None:
        """Get the installed npm version."""
        try:
            result = subprocess.run(
                ["npm", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                # Parse version like "10.2.3"
                version_str = result.stdout.strip()
                parts = version_str.split(".")
                return tuple(int(p) for p in parts[:3])
        except (subprocess.SubprocessError, FileNotFoundError, ValueError):
            pass
        return None

    def get_bundled_source(self) -> Path | None:
        """
        Find the bundled node_listener source.

        Checks:
        1. Package data location (pip installed)
        2. Development location (running from source)
        """
        import importlib.resources

        # Try package data location first
        try:
            # Python 3.9+
            with importlib.resources.as_file(
                importlib.resources.files("wingman").joinpath("../../../node_listener")
            ) as path:
                if path.exists() and (path / "package.json").exists():
                    return path
        except (TypeError, FileNotFoundError):
            pass

        # Try shared data location (pip installed with pyproject.toml shared-data)
        import sys
        for path in [
            Path(sys.prefix) / "share" / "wingman" / "node_listener",
            Path.home() / ".local" / "share" / "wingman" / "node_listener",
        ]:
            if path.exists() and (path / "package.json").exists():
                return path

        # Try development location (relative to this file)
        dev_path = Path(__file__).parent.parent.parent.parent.parent / "node_listener"
        if dev_path.exists() and (dev_path / "package.json").exists():
            return dev_path

        return None

    def install(self, progress_callback=None) -> bool:
        """
        Install the Node.js listener.

        Args:
            progress_callback: Optional callback(step, message) for progress updates

        Returns:
            True if installation succeeded
        """
        def report(step: str, message: str):
            logger.info(f"[{step}] {message}")
            if progress_callback:
                progress_callback(step, message)

        # Find bundled source
        source_dir = self.get_bundled_source()
        if source_dir is None:
            report("error", "Could not find bundled node_listener source")
            return False

        report("copy", f"Copying source from {source_dir}")

        # Create target directory
        self.target_dir.mkdir(parents=True, exist_ok=True)

        # Copy source files (excluding node_modules and dist)
        try:
            self._copy_source(source_dir, self.target_dir)
        except Exception as e:
            report("error", f"Failed to copy source: {e}")
            return False

        report("npm_install", "Installing npm dependencies...")

        # Run npm install
        try:
            result = subprocess.run(
                ["npm", "install"],
                cwd=str(self.target_dir),
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            if result.returncode != 0:
                report("error", f"npm install failed: {result.stderr}")
                return False
        except subprocess.TimeoutExpired:
            report("error", "npm install timed out")
            return False
        except Exception as e:
            report("error", f"npm install failed: {e}")
            return False

        report("npm_build", "Building TypeScript...")

        # Run npm run build
        try:
            result = subprocess.run(
                ["npm", "run", "build"],
                cwd=str(self.target_dir),
                capture_output=True,
                text=True,
                timeout=120  # 2 minute timeout
            )
            if result.returncode != 0:
                report("error", f"npm run build failed: {result.stderr}")
                return False
        except subprocess.TimeoutExpired:
            report("error", "npm run build timed out")
            return False
        except Exception as e:
            report("error", f"npm run build failed: {e}")
            return False

        # Verify installation
        dist_file = self.target_dir / "dist" / "index.js"
        if not dist_file.exists():
            report("error", "Build completed but dist/index.js not found")
            return False

        report("done", "Node.js listener installed successfully")
        return True

    def _copy_source(self, source: Path, target: Path) -> None:
        """Copy source files, excluding node_modules and dist."""
        # Items to exclude
        exclude = {"node_modules", "dist", ".git", "__pycache__"}

        for item in source.iterdir():
            if item.name in exclude:
                continue

            target_item = target / item.name

            if item.is_dir():
                if target_item.exists():
                    shutil.rmtree(target_item)
                shutil.copytree(item, target_item, ignore=shutil.ignore_patterns(*exclude))
            else:
                shutil.copy2(item, target_item)

    def is_installed(self) -> bool:
        """Check if the node_listener is already installed and built."""
        return (
            self.target_dir.exists() and
            (self.target_dir / "package.json").exists() and
            (self.target_dir / "dist" / "index.js").exists()
        )

    def get_version_info(self) -> dict:
        """Get version information for diagnostics."""
        node_version = self._get_node_version()
        npm_version = self._get_npm_version()

        return {
            "node_version": ".".join(map(str, node_version)) if node_version else None,
            "npm_version": ".".join(map(str, npm_version)) if npm_version else None,
            "target_dir": str(self.target_dir),
            "is_installed": self.is_installed(),
            "bundled_source": str(self.get_bundled_source()) if self.get_bundled_source() else None,
        }
