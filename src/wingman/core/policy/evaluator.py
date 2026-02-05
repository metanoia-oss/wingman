"""Policy evaluation engine for determining response behavior."""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import yaml

from wingman.config.registry import (
    ContactProfile,
    ContactRole,
    GroupConfig,
    GroupCategory,
    ReplyPolicy,
)

logger = logging.getLogger(__name__)


@dataclass
class MessageContext:
    """Context information for a message being evaluated."""
    # Message details
    chat_id: str
    sender_id: str
    text: str

    # Chat type
    is_dm: bool
    is_group: bool

    # Resolved profiles
    contact: ContactProfile

    # Optional fields with defaults
    group: Optional[GroupConfig] = None
    platform: str = "whatsapp"
    is_reply_to_bot: bool = False
    is_mentioned: bool = False

    @property
    def role(self) -> ContactRole:
        """Get the sender's role."""
        return self.contact.role

    @property
    def group_category(self) -> Optional[GroupCategory]:
        """Get the group category if in a group."""
        return self.group.category if self.group else None


@dataclass
class PolicyDecision:
    """Result of policy evaluation."""
    should_respond: bool
    reason: str
    rule_name: Optional[str] = None
    action: ReplyPolicy = ReplyPolicy.SELECTIVE


@dataclass
class PolicyRule:
    """A single policy rule."""
    name: str
    conditions: dict
    action: ReplyPolicy

    @classmethod
    def from_dict(cls, data: dict) -> "PolicyRule":
        """Create a PolicyRule from config dict."""
        return cls(
            name=data.get("name", "unnamed"),
            conditions=data.get("conditions", {}),
            action=ReplyPolicy(data.get("action", "selective")),
        )


class PolicyEvaluator:
    """
    Evaluates policy rules against message context to determine
    whether the bot should respond.
    """

    def __init__(self, config_path: Optional[Path] = None, bot_name: str = "Maximus"):
        self._rules: list[PolicyRule] = []
        self._fallback_action = ReplyPolicy.SELECTIVE
        self._bot_name = bot_name.lower()

        if config_path and config_path.exists():
            self._load_config(config_path)

    def _load_config(self, config_path: Path) -> None:
        """Load policy configuration from YAML file."""
        try:
            with open(config_path, "r") as f:
                config = yaml.safe_load(f) or {}

            # Load rules
            rules_data = config.get("rules", [])
            for rule_data in rules_data:
                try:
                    rule = PolicyRule.from_dict(rule_data)
                    self._rules.append(rule)
                    logger.debug(f"Loaded policy rule: {rule.name}")
                except (ValueError, KeyError) as e:
                    logger.warning(f"Invalid policy rule: {e}")

            # Load fallback
            fallback_data = config.get("fallback", {})
            if fallback_data:
                self._fallback_action = ReplyPolicy(
                    fallback_data.get("action", "selective")
                )

            logger.info(f"Loaded {len(self._rules)} policy rules from {config_path}")

        except Exception as e:
            logger.error(f"Failed to load policies config: {e}")

    def _check_mentioned(self, text: str) -> bool:
        """Check if the bot is mentioned in the text."""
        if not text:
            return False

        text_lower = text.lower()

        # Check for @mention or name mention
        if f"@{self._bot_name}" in text_lower:
            return True
        if self._bot_name in text_lower:
            return True

        return False

    def _matches_conditions(self, rule: PolicyRule, context: MessageContext) -> bool:
        """Check if a rule's conditions match the message context."""
        conditions = rule.conditions

        # Check platform
        if "platform" in conditions:
            if conditions["platform"] != context.platform:
                return False

        # Check is_dm
        if "is_dm" in conditions:
            if conditions["is_dm"] != context.is_dm:
                return False

        # Check is_group
        if "is_group" in conditions:
            if conditions["is_group"] != context.is_group:
                return False

        # Check role
        if "role" in conditions:
            if conditions["role"] != context.role.value:
                return False

        # Check group_category
        if "group_category" in conditions:
            if context.group_category is None:
                return False
            if conditions["group_category"] != context.group_category.value:
                return False

        # Check is_reply_to_bot
        if "is_reply_to_bot" in conditions:
            if conditions["is_reply_to_bot"] != context.is_reply_to_bot:
                return False

        # Check is_mentioned
        if "is_mentioned" in conditions:
            if conditions["is_mentioned"] != context.is_mentioned:
                return False

        return True

    def evaluate(self, context: MessageContext) -> PolicyDecision:
        """
        Evaluate policy rules against the message context.

        Args:
            context: The message context to evaluate

        Returns:
            PolicyDecision with should_respond and reason
        """
        # Check if bot is mentioned (for selective policies)
        is_mentioned = self._check_mentioned(context.text)
        # Update context with mention status
        context.is_mentioned = is_mentioned

        logger.debug(
            f"Evaluating policy: platform={context.platform}, is_dm={context.is_dm}, "
            f"role={context.role.value}, "
            f"group_category={context.group_category.value if context.group_category else 'N/A'}, "
            f"is_mentioned={is_mentioned}"
        )

        # Evaluate rules in order
        for rule in self._rules:
            if self._matches_conditions(rule, context):
                logger.debug(f"Rule matched: {rule.name} -> {rule.action.value}")

                should_respond = self._should_respond_for_action(
                    rule.action, is_mentioned, context.is_reply_to_bot
                )

                return PolicyDecision(
                    should_respond=should_respond,
                    reason=f"rule:{rule.name}",
                    rule_name=rule.name,
                    action=rule.action,
                )

        # No rule matched, use fallback
        logger.debug(f"No rule matched, using fallback: {self._fallback_action.value}")
        should_respond = self._should_respond_for_action(
            self._fallback_action, is_mentioned, context.is_reply_to_bot
        )

        return PolicyDecision(
            should_respond=should_respond,
            reason="fallback",
            rule_name=None,
            action=self._fallback_action,
        )

    def _should_respond_for_action(
        self,
        action: ReplyPolicy,
        is_mentioned: bool,
        is_reply_to_bot: bool
    ) -> bool:
        """Determine if should respond based on action type."""
        if action == ReplyPolicy.ALWAYS:
            return True
        elif action == ReplyPolicy.NEVER:
            return False
        elif action == ReplyPolicy.SELECTIVE:
            # Respond if mentioned or replying to bot
            return is_mentioned or is_reply_to_bot
        return False

    def create_context(
        self,
        chat_id: str,
        sender_id: str,
        text: str,
        is_group: bool,
        contact: ContactProfile,
        group: Optional[GroupConfig] = None,
        is_reply_to_bot: bool = False,
        platform: str = "whatsapp",
    ) -> MessageContext:
        """Helper to create a MessageContext."""
        return MessageContext(
            chat_id=chat_id,
            sender_id=sender_id,
            text=text,
            is_dm=not is_group,
            is_group=is_group,
            platform=platform,
            contact=contact,
            group=group,
            is_reply_to_bot=is_reply_to_bot,
        )
