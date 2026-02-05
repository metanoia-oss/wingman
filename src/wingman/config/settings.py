"""Configuration settings loaded from environment or YAML."""

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

from .paths import WingmanPaths

logger = logging.getLogger(__name__)


@dataclass
class Settings:
    """Application settings loaded from YAML config or environment variables."""

    # OpenAI
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"

    # Bot identity
    bot_name: str = "Maximus"

    # Safety limits
    max_replies_per_hour: int = 30
    default_cooldown_seconds: int = 60
    quiet_hours_start: int = 0  # Midnight
    quiet_hours_end: int = 6    # 6 AM
    quiet_hours_enabled: bool = True

    # LLM settings
    context_window_size: int = 30
    max_response_tokens: int = 150
    temperature: float = 0.8

    # iMessage settings
    imessage_enabled: bool = False
    imessage_poll_interval: float = 2.0
    imessage_max_replies_per_hour: int = 15
    imessage_cooldown: int = 120

    # Paths (set after loading)
    node_dir: Path = field(default_factory=Path)
    data_dir: Path = field(default_factory=Path)
    log_dir: Path = field(default_factory=Path)
    db_path: Path = field(default_factory=Path)
    auth_state_dir: Path = field(default_factory=Path)

    # Config file paths
    contacts_config: Path = field(default_factory=Path)
    groups_config: Path = field(default_factory=Path)
    policies_config: Path = field(default_factory=Path)

    # Source mode
    _is_cli_mode: bool = False

    @classmethod
    def load(cls, env_path: Path | None = None, paths: WingmanPaths | None = None) -> "Settings":
        """
        Load settings with fallback chain:
        1. YAML config file (if paths provided and config exists)
        2. Environment variables
        3. Defaults
        """
        # Determine paths
        if paths is None:
            # Try CLI mode first (XDG paths)
            paths = WingmanPaths()
            if paths.config_exists():
                return cls._load_from_yaml(paths)

            # Fall back to legacy mode (project root)
            project_root = Path(__file__).parent.parent.parent.parent
            if (project_root / ".env").exists() or (project_root / "node_listener").exists():
                return cls._load_from_env(project_root, env_path)

            # No config found, use XDG paths with env vars
            return cls._load_from_env_with_paths(paths, env_path)
        else:
            if paths.config_exists():
                return cls._load_from_yaml(paths)
            else:
                return cls._load_from_env_with_paths(paths, env_path)

    @classmethod
    def _load_from_yaml(cls, paths: WingmanPaths) -> "Settings":
        """Load settings from YAML config file."""
        config_file = paths.config_file
        logger.info(f"Loading settings from {config_file}")

        with open(config_file) as f:
            config = yaml.safe_load(f) or {}

        # Parse config sections
        bot_config = config.get("bot", {})
        openai_config = config.get("openai", {})
        safety_config = config.get("safety", {})
        quiet_hours_config = safety_config.get("quiet_hours", {})
        imessage_config = config.get("imessage", {})

        # Get API key from config or environment
        api_key = openai_config.get("api_key") or os.getenv("OPENAI_API_KEY", "")

        settings = cls(
            # OpenAI
            openai_api_key=api_key,
            openai_model=openai_config.get("model", "gpt-4o"),

            # Bot identity
            bot_name=bot_config.get("name", "Maximus"),

            # Safety limits
            max_replies_per_hour=safety_config.get("max_replies_per_hour", 30),
            default_cooldown_seconds=safety_config.get("cooldown_seconds", 60),
            quiet_hours_start=quiet_hours_config.get("start", 0),
            quiet_hours_end=quiet_hours_config.get("end", 6),
            quiet_hours_enabled=quiet_hours_config.get("enabled", True),

            # LLM settings
            context_window_size=openai_config.get("context_window_size", 30),
            max_response_tokens=openai_config.get("max_response_tokens", 150),
            temperature=openai_config.get("temperature", 0.8),

            # iMessage settings
            imessage_enabled=imessage_config.get("enabled", False),
            imessage_poll_interval=imessage_config.get("poll_interval", 2.0),
            imessage_max_replies_per_hour=imessage_config.get("max_replies_per_hour", 15),
            imessage_cooldown=imessage_config.get("cooldown", 120),

            # Paths from WingmanPaths
            node_dir=paths.node_dir,
            data_dir=paths.data_dir,
            log_dir=paths.log_dir,
            db_path=paths.db_path,
            auth_state_dir=paths.auth_state_dir,
            contacts_config=paths.contacts_config,
            groups_config=paths.groups_config,
            policies_config=paths.policies_config,

            _is_cli_mode=True,
        )

        # Ensure directories exist
        paths.ensure_directories()

        logger.info(f"Settings loaded: bot_name={settings.bot_name}, model={settings.openai_model}")
        return settings

    @classmethod
    def _load_from_env(cls, project_root: Path, env_path: Path | None = None) -> "Settings":
        """Load settings from environment variables (legacy mode)."""
        # Load .env file
        if env_path:
            load_dotenv(env_path)
        else:
            load_dotenv(project_root / ".env")

        settings = cls(
            # OpenAI
            openai_api_key=os.getenv("OPENAI_API_KEY", ""),
            openai_model=os.getenv("OPENAI_MODEL", "gpt-4o"),

            # Bot identity
            bot_name=os.getenv("BOT_NAME", "Maximus"),

            # Safety limits
            max_replies_per_hour=int(os.getenv("MAX_REPLIES_PER_HOUR", "30")),
            default_cooldown_seconds=int(os.getenv("DEFAULT_COOLDOWN_SECONDS", "60")),
            quiet_hours_start=int(os.getenv("QUIET_HOURS_START", "0")),
            quiet_hours_end=int(os.getenv("QUIET_HOURS_END", "6")),

            # LLM settings
            context_window_size=int(os.getenv("CONTEXT_WINDOW_SIZE", "30")),
            max_response_tokens=int(os.getenv("MAX_RESPONSE_TOKENS", "150")),
            temperature=float(os.getenv("TEMPERATURE", "0.8")),

            # iMessage settings
            imessage_enabled=os.getenv("IMESSAGE_ENABLED", "false").lower() == "true",
            imessage_poll_interval=float(os.getenv("IMESSAGE_POLL_INTERVAL", "2.0")),
            imessage_max_replies_per_hour=int(os.getenv("IMESSAGE_MAX_REPLIES_PER_HOUR", "15")),
            imessage_cooldown=int(os.getenv("IMESSAGE_COOLDOWN", "120")),

            # Paths (legacy project structure)
            node_dir=project_root / "node_listener",
            data_dir=project_root / "data",
            log_dir=project_root / "logs",
            db_path=project_root / "data" / "conversations.db",
            auth_state_dir=project_root / "auth_state",
            contacts_config=project_root / "config" / "contacts.yaml",
            groups_config=project_root / "config" / "groups.yaml",
            policies_config=project_root / "config" / "policies.yaml",

            _is_cli_mode=False,
        )

        # Validate required settings
        if not settings.openai_api_key:
            logger.warning("OPENAI_API_KEY not set - LLM features will fail")

        # Ensure directories exist
        settings.data_dir.mkdir(parents=True, exist_ok=True)
        settings.log_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Settings loaded: bot_name={settings.bot_name}, model={settings.openai_model}")
        return settings

    @classmethod
    def _load_from_env_with_paths(cls, paths: WingmanPaths, env_path: Path | None = None) -> "Settings":
        """Load settings from environment variables with XDG paths."""
        if env_path:
            load_dotenv(env_path)

        settings = cls(
            # OpenAI
            openai_api_key=os.getenv("OPENAI_API_KEY", ""),
            openai_model=os.getenv("OPENAI_MODEL", "gpt-4o"),

            # Bot identity
            bot_name=os.getenv("BOT_NAME", "Maximus"),

            # Safety limits
            max_replies_per_hour=int(os.getenv("MAX_REPLIES_PER_HOUR", "30")),
            default_cooldown_seconds=int(os.getenv("DEFAULT_COOLDOWN_SECONDS", "60")),
            quiet_hours_start=int(os.getenv("QUIET_HOURS_START", "0")),
            quiet_hours_end=int(os.getenv("QUIET_HOURS_END", "6")),

            # LLM settings
            context_window_size=int(os.getenv("CONTEXT_WINDOW_SIZE", "30")),
            max_response_tokens=int(os.getenv("MAX_RESPONSE_TOKENS", "150")),
            temperature=float(os.getenv("TEMPERATURE", "0.8")),

            # iMessage settings
            imessage_enabled=os.getenv("IMESSAGE_ENABLED", "false").lower() == "true",
            imessage_poll_interval=float(os.getenv("IMESSAGE_POLL_INTERVAL", "2.0")),
            imessage_max_replies_per_hour=int(os.getenv("IMESSAGE_MAX_REPLIES_PER_HOUR", "15")),
            imessage_cooldown=int(os.getenv("IMESSAGE_COOLDOWN", "120")),

            # Paths from WingmanPaths
            node_dir=paths.node_dir,
            data_dir=paths.data_dir,
            log_dir=paths.log_dir,
            db_path=paths.db_path,
            auth_state_dir=paths.auth_state_dir,
            contacts_config=paths.contacts_config,
            groups_config=paths.groups_config,
            policies_config=paths.policies_config,

            _is_cli_mode=True,
        )

        paths.ensure_directories()
        return settings

    def validate(self) -> list[str]:
        """Validate settings and return list of errors."""
        errors = []

        if not self.openai_api_key:
            errors.append("OPENAI_API_KEY is required")

        if not self.node_dir.exists():
            errors.append(f"Node listener directory not found: {self.node_dir}")

        if not (self.node_dir / "dist" / "index.js").exists():
            errors.append(
                f"Node listener not built. Run 'wingman init' or manually build: "
                f"cd {self.node_dir} && npm install && npm run build"
            )

        if not 0 <= self.quiet_hours_start <= 23:
            errors.append("quiet_hours_start must be 0-23")

        if not 0 <= self.quiet_hours_end <= 23:
            errors.append("quiet_hours_end must be 0-23")

        return errors

    def to_yaml_dict(self) -> dict[str, Any]:
        """Convert settings to a dictionary suitable for YAML serialization."""
        return {
            "bot": {
                "name": self.bot_name,
            },
            "openai": {
                "api_key": self.openai_api_key,
                "model": self.openai_model,
                "context_window_size": self.context_window_size,
                "max_response_tokens": self.max_response_tokens,
                "temperature": self.temperature,
            },
            "safety": {
                "max_replies_per_hour": self.max_replies_per_hour,
                "cooldown_seconds": self.default_cooldown_seconds,
                "quiet_hours": {
                    "enabled": self.quiet_hours_enabled,
                    "start": self.quiet_hours_start,
                    "end": self.quiet_hours_end,
                },
            },
            "imessage": {
                "enabled": self.imessage_enabled,
                "poll_interval": self.imessage_poll_interval,
                "max_replies_per_hour": self.imessage_max_replies_per_hour,
                "cooldown": self.imessage_cooldown,
            },
        }
