"""Configuration settings loaded from environment."""

import os
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


@dataclass
class Settings:
    """Application settings loaded from environment variables."""

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

    # LLM settings
    context_window_size: int = 30
    max_response_tokens: int = 150
    temperature: float = 0.8

    # iMessage settings
    imessage_enabled: bool = False
    imessage_poll_interval: float = 2.0
    imessage_max_replies_per_hour: int = 15  # Stricter than WhatsApp
    imessage_cooldown: int = 120  # Longer cooldown

    # Paths (set after loading)
    project_root: Path = field(default_factory=Path)
    node_dir: Path = field(default_factory=Path)
    data_dir: Path = field(default_factory=Path)
    log_dir: Path = field(default_factory=Path)
    db_path: Path = field(default_factory=Path)

    # Config file paths
    contacts_config: Path = field(default_factory=Path)
    groups_config: Path = field(default_factory=Path)
    policies_config: Path = field(default_factory=Path)

    @classmethod
    def load(cls, env_path: Optional[Path] = None) -> "Settings":
        """Load settings from environment variables."""
        # Find project root (directory containing this config package)
        project_root = Path(__file__).parent.parent

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

            # Paths
            project_root=project_root,
            node_dir=project_root / "node_listener",
            data_dir=project_root / "data",
            log_dir=project_root / "logs",
            db_path=project_root / "data" / "conversations.db",

            # Config file paths
            contacts_config=project_root / "config" / "contacts.yaml",
            groups_config=project_root / "config" / "groups.yaml",
            policies_config=project_root / "config" / "policies.yaml",
        )

        # Validate required settings
        if not settings.openai_api_key:
            logger.warning("OPENAI_API_KEY not set - LLM features will fail")

        # Ensure directories exist
        settings.data_dir.mkdir(parents=True, exist_ok=True)
        settings.log_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Settings loaded: bot_name={settings.bot_name}, model={settings.openai_model}")
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
                f"Node listener not built. Run: cd {self.node_dir} && npm install && npm run build"
            )

        if not 0 <= self.quiet_hours_start <= 23:
            errors.append("quiet_hours_start must be 0-23")

        if not 0 <= self.quiet_hours_end <= 23:
            errors.append("quiet_hours_end must be 0-23")

        return errors
