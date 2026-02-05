"""Trigger word and mention detection."""

import logging
import re

logger = logging.getLogger(__name__)


class TriggerDetector:
    """
    Detects trigger words, mentions, and other conditions that should
    cause the bot to respond.
    """

    def __init__(
        self,
        bot_name: str = "Maximus",
        additional_triggers: list[str] | None = None
    ):
        self.bot_name = bot_name.lower()
        self.triggers: set[str] = {self.bot_name}

        # Add common variations
        self.triggers.add(f"@{self.bot_name}")

        # Add additional triggers
        if additional_triggers:
            for trigger in additional_triggers:
                self.triggers.add(trigger.lower())

        # Compile regex patterns for efficient matching
        self._compile_patterns()

    def _compile_patterns(self) -> None:
        """Compile regex patterns for trigger matching."""
        # Pattern for @mentions (handles WhatsApp mention format)
        escaped_triggers = [re.escape(t) for t in self.triggers]
        pattern = r'\b(' + '|'.join(escaped_triggers) + r')\b'
        self._trigger_pattern = re.compile(pattern, re.IGNORECASE)

    def add_trigger(self, trigger: str) -> None:
        """Add a new trigger word."""
        self.triggers.add(trigger.lower())
        self._compile_patterns()
        logger.debug(f"Added trigger: {trigger}")

    def remove_trigger(self, trigger: str) -> None:
        """Remove a trigger word."""
        self.triggers.discard(trigger.lower())
        self._compile_patterns()
        logger.debug(f"Removed trigger: {trigger}")

    def has_trigger(self, text: str) -> bool:
        """
        Check if the text contains any trigger words.

        Args:
            text: Message text to check

        Returns:
            True if a trigger is found
        """
        if not text:
            return False

        match = self._trigger_pattern.search(text)
        if match:
            logger.debug(f"Trigger found: '{match.group()}'")
            return True
        return False

    def is_direct_mention(self, text: str) -> bool:
        """
        Check if the message starts with a mention of the bot.
        This indicates a direct address.
        """
        if not text:
            return False

        text_lower = text.lower().strip()

        for trigger in self.triggers:
            if text_lower.startswith(trigger):
                return True
            # Check for @mention at start
            if text_lower.startswith(f"@{trigger}"):
                return True

        return False

    def should_respond(
        self,
        text: str,
        is_group: bool,
        is_dm: bool = False,
        is_reply_to_bot: bool = False
    ) -> tuple[bool, str]:
        """
        Determine if the bot should respond to this message.

        Args:
            text: Message text
            is_group: Whether this is a group chat
            is_dm: Whether this is a direct message
            is_reply_to_bot: Whether this is a reply to the bot's message

        Returns:
            Tuple of (should_respond, reason)
        """
        # Always respond to DMs
        if is_dm:
            return True, "direct_message"

        # Always respond if replying to bot's message
        if is_reply_to_bot:
            return True, "reply_to_bot"

        # In groups, only respond to triggers
        if is_group:
            if self.has_trigger(text):
                return True, "trigger_word"
            return False, "no_trigger"

        # Default: don't respond
        return False, "no_match"
