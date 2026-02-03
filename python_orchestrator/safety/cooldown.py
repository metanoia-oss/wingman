"""Per-chat cooldown management."""

import time
import logging
from typing import Dict

logger = logging.getLogger(__name__)


class CooldownManager:
    """
    Manages per-chat cooldowns to prevent rapid-fire responses.
    """

    def __init__(self, default_cooldown_seconds: int = 60):
        self.default_cooldown = default_cooldown_seconds
        self._last_reply: Dict[str, float] = {}
        self._custom_cooldowns: Dict[str, int] = {}

    def set_cooldown(self, chat_id: str, seconds: int) -> None:
        """Set a custom cooldown for a specific chat."""
        self._custom_cooldowns[chat_id] = seconds
        logger.debug(f"Set custom cooldown for {chat_id}: {seconds}s")

    def get_cooldown(self, chat_id: str) -> int:
        """Get the cooldown duration for a chat."""
        return self._custom_cooldowns.get(chat_id, self.default_cooldown)

    def is_on_cooldown(self, chat_id: str) -> bool:
        """Check if a chat is currently on cooldown."""
        last_reply = self._last_reply.get(chat_id)
        if last_reply is None:
            return False

        cooldown = self.get_cooldown(chat_id)
        elapsed = time.time() - last_reply
        on_cooldown = elapsed < cooldown

        if on_cooldown:
            remaining = cooldown - elapsed
            logger.debug(f"Chat {chat_id} on cooldown: {remaining:.1f}s remaining")

        return on_cooldown

    def record_reply(self, chat_id: str) -> None:
        """Record that a reply was sent to a chat."""
        self._last_reply[chat_id] = time.time()
        logger.debug(f"Recorded reply to {chat_id}")

    def get_remaining_cooldown(self, chat_id: str) -> float:
        """Get seconds remaining in cooldown, or 0 if not on cooldown."""
        last_reply = self._last_reply.get(chat_id)
        if last_reply is None:
            return 0

        cooldown = self.get_cooldown(chat_id)
        elapsed = time.time() - last_reply
        return max(0, cooldown - elapsed)

    def clear_cooldown(self, chat_id: str) -> None:
        """Manually clear cooldown for a chat."""
        if chat_id in self._last_reply:
            del self._last_reply[chat_id]
            logger.debug(f"Cleared cooldown for {chat_id}")
