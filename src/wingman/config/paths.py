"""XDG-compliant path management for Wingman."""

from pathlib import Path

from platformdirs import user_cache_dir, user_config_dir, user_data_dir


class WingmanPaths:
    """
    Manages XDG-compliant paths for Wingman configuration and data.

    Directories:
    - config_dir: ~/.config/wingman/ - Configuration files (YAML configs)
    - data_dir: ~/.local/share/wingman/ - Data files (DB, auth state)
    - cache_dir: ~/.cache/wingman/ - Cache and logs
    - node_dir: ~/.config/wingman/node_listener/ - Installed Node.js listener
    """

    APP_NAME = "wingman"
    APP_AUTHOR = "wingman"

    def __init__(
        self,
        config_dir: Path | None = None,
        data_dir: Path | None = None,
        cache_dir: Path | None = None,
    ):
        """
        Initialize Wingman paths.

        Args:
            config_dir: Override config directory (default: ~/.config/wingman)
            data_dir: Override data directory (default: ~/.local/share/wingman)
            cache_dir: Override cache directory (default: ~/.cache/wingman)
        """
        self._config_dir = config_dir or Path(user_config_dir(self.APP_NAME, self.APP_AUTHOR))
        self._data_dir = data_dir or Path(user_data_dir(self.APP_NAME, self.APP_AUTHOR))
        self._cache_dir = cache_dir or Path(user_cache_dir(self.APP_NAME, self.APP_AUTHOR))

    @property
    def config_dir(self) -> Path:
        """Config directory (~/.config/wingman/)."""
        return self._config_dir

    @property
    def data_dir(self) -> Path:
        """Data directory (~/.local/share/wingman/)."""
        return self._data_dir

    @property
    def cache_dir(self) -> Path:
        """Cache directory (~/.cache/wingman/)."""
        return self._cache_dir

    @property
    def log_dir(self) -> Path:
        """Log directory (~/.cache/wingman/logs/)."""
        return self._cache_dir / "logs"

    @property
    def node_dir(self) -> Path:
        """Node.js listener directory (~/.config/wingman/node_listener/)."""
        return self._config_dir / "node_listener"

    @property
    def auth_state_dir(self) -> Path:
        """WhatsApp auth state directory (~/.local/share/wingman/auth_state/)."""
        return self._data_dir / "auth_state"

    @property
    def db_path(self) -> Path:
        """Database file path (~/.local/share/wingman/conversations.db)."""
        return self._data_dir / "conversations.db"

    @property
    def config_file(self) -> Path:
        """Main config file (~/.config/wingman/config.yaml)."""
        return self._config_dir / "config.yaml"

    @property
    def contacts_config(self) -> Path:
        """Contacts config file (~/.config/wingman/contacts.yaml)."""
        return self._config_dir / "contacts.yaml"

    @property
    def groups_config(self) -> Path:
        """Groups config file (~/.config/wingman/groups.yaml)."""
        return self._config_dir / "groups.yaml"

    @property
    def policies_config(self) -> Path:
        """Policies config file (~/.config/wingman/policies.yaml)."""
        return self._config_dir / "policies.yaml"

    @property
    def personality_config(self) -> Path:
        """Personality config file (~/.config/wingman/personality.yaml)."""
        return self._config_dir / "personality.yaml"

    @property
    def pid_file(self) -> Path:
        """PID file for daemon (~/.cache/wingman/wingman.pid)."""
        return self._cache_dir / "wingman.pid"

    @property
    def launchd_plist(self) -> Path:
        """Launchd plist file (~/Library/LaunchAgents/com.wingman.agent.plist)."""
        return Path.home() / "Library" / "LaunchAgents" / "com.wingman.agent.plist"

    def ensure_directories(self) -> None:
        """Create all required directories if they don't exist."""
        for directory in [
            self._config_dir,
            self._data_dir,
            self._cache_dir,
            self.log_dir,
            self.auth_state_dir,
        ]:
            directory.mkdir(parents=True, exist_ok=True)

    def config_exists(self) -> bool:
        """Check if the main config file exists."""
        return self.config_file.exists()

    def is_initialized(self) -> bool:
        """Check if Wingman has been set up (config and node_listener exist)."""
        return (
            self.config_file.exists() and
            self.node_dir.exists() and
            (self.node_dir / "dist" / "index.js").exists()
        )

    @classmethod
    def from_project_root(cls, project_root: Path) -> "WingmanPaths":
        """
        Create paths relative to a project root (for development/legacy mode).

        This maintains backward compatibility with the original project structure.
        """
        return cls(
            config_dir=project_root / "config",
            data_dir=project_root / "data",
            cache_dir=project_root / "logs",
        )

    def __repr__(self) -> str:
        return (
            f"WingmanPaths(\n"
            f"  config_dir={self._config_dir}\n"
            f"  data_dir={self._data_dir}\n"
            f"  cache_dir={self._cache_dir}\n"
            f")"
        )
