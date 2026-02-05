"""Contact and Group Registry for config-driven identity resolution."""

import logging
import os
import threading
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)


class ContactRole(Enum):
    """Role categories for contacts."""
    GIRLFRIEND = "girlfriend"
    SISTER = "sister"
    FRIEND = "friend"
    FAMILY = "family"
    COLLEAGUE = "colleague"
    UNKNOWN = "unknown"


class ContactTone(Enum):
    """Tone styles for responses."""
    AFFECTIONATE = "affectionate"  # Warm, pet names, supportive
    LOVING = "loving"              # Deep affection, intimate
    FRIENDLY = "friendly"          # Sibling vibes, playful teasing
    CASUAL = "casual"              # Relaxed friend energy
    SARCASTIC = "sarcastic"        # Witty, playful sarcasm
    NEUTRAL = "neutral"            # Polite acquaintance


class GroupCategory(Enum):
    """Categories for group chats."""
    FAMILY = "family"
    FRIENDS = "friends"
    WORK = "work"
    UNKNOWN = "unknown"


class ReplyPolicy(Enum):
    """Reply policies for chats."""
    ALWAYS = "always"        # Always respond
    SELECTIVE = "selective"  # Only when mentioned
    NEVER = "never"          # Never respond


@dataclass
class ContactProfile:
    """Profile for a known contact."""
    jid: str
    name: str
    role: ContactRole
    tone: ContactTone
    allow_proactive: bool = False
    cooldown_override: int | None = None
    imessage_id: str | None = None  # Linked iMessage identifier

    @classmethod
    def from_dict(cls, jid: str, data: dict) -> "ContactProfile":
        """Create a ContactProfile from config dict."""
        return cls(
            jid=jid,
            name=data.get("name", "Unknown"),
            role=ContactRole(data.get("role", "unknown")),
            tone=ContactTone(data.get("tone", "neutral")),
            allow_proactive=data.get("allow_proactive", False),
            cooldown_override=data.get("cooldown_override"),
            imessage_id=data.get("imessage_id"),
        )


@dataclass
class GroupConfig:
    """Configuration for a group chat."""
    jid: str
    name: str
    category: GroupCategory
    reply_policy: ReplyPolicy

    @classmethod
    def from_dict(cls, jid: str, data: dict) -> "GroupConfig":
        """Create a GroupConfig from config dict."""
        return cls(
            jid=jid,
            name=data.get("name", "Unknown Group"),
            category=GroupCategory(data.get("category", "unknown")),
            reply_policy=ReplyPolicy(data.get("reply_policy", "selective")),
        )


@dataclass
class ContactDefaults:
    """Default values for unknown contacts."""
    role: ContactRole = ContactRole.UNKNOWN
    tone: ContactTone = ContactTone.NEUTRAL
    allow_proactive: bool = False
    cooldown_override: int | None = None


@dataclass
class GroupDefaults:
    """Default values for unknown groups."""
    category: GroupCategory = GroupCategory.UNKNOWN
    reply_policy: ReplyPolicy = ReplyPolicy.SELECTIVE


class ContactRegistry:
    """Registry for resolving contact JIDs to profiles."""

    def __init__(self, config_path: Path | None = None, auto_reload: bool = True):
        self._contacts: dict[str, ContactProfile] = {}
        self._imessage_lookup: dict[str, str] = {}  # iMessage ID -> primary JID
        self._defaults = ContactDefaults()
        self._config_path = config_path
        self._last_modified: float = 0
        self._watcher_thread: threading.Thread | None = None
        self._stop_watcher = threading.Event()

        if config_path and config_path.exists():
            self._load_config(config_path)
            if auto_reload:
                self._start_watcher()

    def _load_config(self, config_path: Path) -> None:
        """Load contact configuration from YAML file."""
        try:
            with open(config_path) as f:
                config = yaml.safe_load(f) or {}

            # Load contacts
            contacts_data = config.get("contacts", {})
            for jid, data in contacts_data.items():
                try:
                    profile = ContactProfile.from_dict(jid, data)
                    self._contacts[jid] = profile
                    logger.debug(f"Loaded contact: {profile.name} ({jid})")

                    # Build iMessage lookup table
                    if profile.imessage_id:
                        imessage_key = f"imessage:{profile.imessage_id}"
                        self._imessage_lookup[imessage_key] = jid
                        logger.debug(f"Linked iMessage {profile.imessage_id} to {jid}")
                except (ValueError, KeyError) as e:
                    logger.warning(f"Invalid contact config for {jid}: {e}")

            # Load defaults
            defaults_data = config.get("defaults", {})
            if defaults_data:
                self._defaults = ContactDefaults(
                    role=ContactRole(defaults_data.get("role", "unknown")),
                    tone=ContactTone(defaults_data.get("tone", "neutral")),
                    allow_proactive=defaults_data.get("allow_proactive", False),
                    cooldown_override=defaults_data.get("cooldown_override"),
                )

            self._last_modified = os.path.getmtime(config_path)
            logger.info(f"Loaded {len(self._contacts)} contacts from {config_path}")

        except Exception as e:
            logger.error(f"Failed to load contacts config: {e}")

    def _start_watcher(self) -> None:
        """Start background thread to watch for config changes."""
        if self._watcher_thread is not None:
            return

        def watch():
            while not self._stop_watcher.is_set():
                try:
                    if self._config_path and self._config_path.exists():
                        mtime = os.path.getmtime(self._config_path)
                        if mtime > self._last_modified:
                            logger.info("Contacts config changed, reloading...")
                            self._contacts.clear()
                            self._imessage_lookup.clear()
                            self._load_config(self._config_path)
                except Exception as e:
                    logger.error(f"Error watching contacts config: {e}")
                time.sleep(2)  # Check every 2 seconds

        self._watcher_thread = threading.Thread(target=watch, daemon=True)
        self._watcher_thread.start()
        logger.debug("Started contacts config watcher")

    def stop_watcher(self) -> None:
        """Stop the config watcher thread."""
        self._stop_watcher.set()

    def resolve(self, jid: str) -> ContactProfile:
        """
        Resolve a JID or iMessage identifier to a contact profile.

        Supports:
        - WhatsApp JIDs: "+14155551234@s.whatsapp.net"
        - iMessage identifiers: "imessage:+14155551234" or "imessage:user@icloud.com"

        Returns the configured profile if known, or a default profile if unknown.
        """
        # Direct lookup
        if jid in self._contacts:
            return self._contacts[jid]

        # Try iMessage lookup (maps iMessage ID to WhatsApp contact)
        if jid in self._imessage_lookup:
            primary_jid = self._imessage_lookup[jid]
            return self._contacts[primary_jid]

        # For iMessage identifiers without prefix, try with prefix
        if not jid.startswith("imessage:") and "@" not in jid:
            imessage_key = f"imessage:{jid}"
            if imessage_key in self._contacts:
                return self._contacts[imessage_key]
            if imessage_key in self._imessage_lookup:
                primary_jid = self._imessage_lookup[imessage_key]
                return self._contacts[primary_jid]

        # Return default profile for unknown contacts
        return ContactProfile(
            jid=jid,
            name="Unknown",
            role=self._defaults.role,
            tone=self._defaults.tone,
            allow_proactive=self._defaults.allow_proactive,
            cooldown_override=self._defaults.cooldown_override,
        )

    def is_known(self, jid: str) -> bool:
        """Check if a contact is in the registry."""
        return jid in self._contacts

    def get_all_contacts(self) -> list[ContactProfile]:
        """Get all registered contacts."""
        return list(self._contacts.values())


class GroupRegistry:
    """Registry for resolving group JIDs to configurations."""

    def __init__(self, config_path: Path | None = None, auto_reload: bool = True):
        self._groups: dict[str, GroupConfig] = {}
        self._defaults = GroupDefaults()
        self._config_path = config_path
        self._last_modified: float = 0
        self._watcher_thread: threading.Thread | None = None
        self._stop_watcher = threading.Event()

        if config_path and config_path.exists():
            self._load_config(config_path)
            if auto_reload:
                self._start_watcher()

    def _load_config(self, config_path: Path) -> None:
        """Load group configuration from YAML file."""
        try:
            with open(config_path) as f:
                config = yaml.safe_load(f) or {}

            # Load groups
            groups_data = config.get("groups", {})
            for jid, data in groups_data.items():
                try:
                    group_config = GroupConfig.from_dict(jid, data)
                    self._groups[jid] = group_config
                    logger.debug(f"Loaded group: {group_config.name} ({jid})")
                except (ValueError, KeyError) as e:
                    logger.warning(f"Invalid group config for {jid}: {e}")

            # Load defaults
            defaults_data = config.get("defaults", {})
            if defaults_data:
                self._defaults = GroupDefaults(
                    category=GroupCategory(defaults_data.get("category", "unknown")),
                    reply_policy=ReplyPolicy(defaults_data.get("reply_policy", "selective")),
                )

            self._last_modified = os.path.getmtime(config_path)
            logger.info(f"Loaded {len(self._groups)} groups from {config_path}")

        except Exception as e:
            logger.error(f"Failed to load groups config: {e}")

    def _start_watcher(self) -> None:
        """Start background thread to watch for config changes."""
        if self._watcher_thread is not None:
            return

        def watch():
            while not self._stop_watcher.is_set():
                try:
                    if self._config_path and self._config_path.exists():
                        mtime = os.path.getmtime(self._config_path)
                        if mtime > self._last_modified:
                            logger.info("Groups config changed, reloading...")
                            self._groups.clear()
                            self._load_config(self._config_path)
                except Exception as e:
                    logger.error(f"Error watching groups config: {e}")
                time.sleep(2)  # Check every 2 seconds

        self._watcher_thread = threading.Thread(target=watch, daemon=True)
        self._watcher_thread.start()
        logger.debug("Started groups config watcher")

    def stop_watcher(self) -> None:
        """Stop the config watcher thread."""
        self._stop_watcher.set()

    def resolve(self, jid: str) -> GroupConfig:
        """
        Resolve a group JID to its configuration.

        Returns the configured settings if known, or defaults if unknown.
        """
        if jid in self._groups:
            return self._groups[jid]

        # Return default config for unknown groups
        return GroupConfig(
            jid=jid,
            name="Unknown Group",
            category=self._defaults.category,
            reply_policy=self._defaults.reply_policy,
        )

    def is_known(self, jid: str) -> bool:
        """Check if a group is in the registry."""
        return jid in self._groups

    def get_all_groups(self) -> list[GroupConfig]:
        """Get all registered groups."""
        return list(self._groups.values())
