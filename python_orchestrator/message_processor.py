"""Core message processing logic."""

import logging
import time
from typing import Callable, Coroutine, Dict, Any, Optional

from .memory.models import MessageStore, Message
from .memory.context import ContextBuilder
from .safety import RateLimiter, CooldownManager, QuietHoursChecker, TriggerDetector
from .llm.client import LLMClient
from .policy import PolicyEvaluator, MessageContext
from config.personality import get_personality_prompt, RoleBasedPromptBuilder
from config.registry import ContactRegistry, GroupRegistry, ContactProfile, GroupConfig

logger = logging.getLogger(__name__)

# Type alias for message sender callback
MessageSender = Callable[[str, str, str], Coroutine[Any, Any, bool]]


class MessageProcessor:
    """
    Core orchestrator for processing incoming messages.
    Implements the full message handling flow with safety checks.

    Transport-agnostic: uses a sender callback instead of direct IPC.
    """

    def __init__(
        self,
        store: MessageStore,
        llm: LLMClient,
        contact_registry: ContactRegistry,
        group_registry: GroupRegistry,
        policy_evaluator: PolicyEvaluator,
        bot_name: str = "Maximus",
        max_replies_per_hour: int = 30,
        default_cooldown: int = 60,
        quiet_start: int = 0,
        quiet_end: int = 6,
        context_window: int = 30
    ):
        self.store = store
        self.llm = llm
        self.bot_name = bot_name

        # Config-driven registries
        self.contact_registry = contact_registry
        self.group_registry = group_registry
        self.policy_evaluator = policy_evaluator

        # Initialize safety components
        self.rate_limiter = RateLimiter(max_replies_per_hour)
        self.cooldown = CooldownManager(default_cooldown)
        self.quiet_hours = QuietHoursChecker(quiet_start, quiet_end)
        self.triggers = TriggerDetector(bot_name)  # Keep for fallback

        # Context builder
        self.context_builder = ContextBuilder(store, context_window, bot_name)

        # Role-based prompt builder
        self.prompt_builder = RoleBasedPromptBuilder(bot_name)

        # Track our own user ID per platform
        self.self_ids: Dict[str, str] = {}

        # Message sender callback: (platform, chat_id, text) -> success
        self._send_message: Optional[MessageSender] = None

    def set_self_id(self, user_id: str, platform: str = "whatsapp") -> None:
        """Set our own user ID for self-message detection."""
        self.self_ids[platform] = user_id
        logger.info(f"Self ID set for {platform}: {user_id}")

    def set_sender(self, sender: MessageSender) -> None:
        """Set the message sender callback."""
        self._send_message = sender

    async def process_message(self, data: Dict[str, Any]) -> None:
        """
        Process an incoming message through the full pipeline.

        Flow:
        1. Store message in SQLite
        2. Check safety rules
        3. Check for triggers
        4. Generate and send response
        """
        chat_id = data.get('chatId', '')
        sender_id = data.get('senderId', '')
        sender_name = data.get('senderName')
        text = data.get('text', '')
        timestamp = data.get('timestamp', time.time())
        is_group = data.get('isGroup', False)
        is_self = data.get('isSelf', False)
        platform = data.get('platform', 'whatsapp')

        logger.info(
            f"Processing message: platform={platform}, chat={chat_id[:20]}..., "
            f"sender={sender_name or sender_id[:15]}..., "
            f"text={text[:50]}..."
        )

        # 1. Always store the message
        message = Message(
            id=None,
            chat_id=chat_id,
            sender_id=sender_id,
            sender_name=sender_name,
            text=text,
            timestamp=timestamp,
            is_self=is_self,
            platform=platform
        )
        self.store.store_message(message)

        # Don't process our own messages
        if is_self:
            logger.debug("Skipping self message")
            return

        # 2. Resolve contact and group profiles
        contact = self.contact_registry.resolve(sender_id)
        group = self.group_registry.resolve(chat_id) if is_group else None

        logger.info(
            f"Resolved: contact={contact.name} (role={contact.role.value}, tone={contact.tone.value})"
            + (f", group={group.name} (category={group.category.value})" if group else "")
        )

        # 3. Apply per-contact cooldown override if configured
        if contact.cooldown_override is not None:
            self.cooldown.set_cooldown(chat_id, contact.cooldown_override)

        # 4. Check safety rules
        skip_reason = self._check_safety_rules(chat_id)
        if skip_reason:
            logger.info(f"Skipping message: {skip_reason}")
            return

        # 5. Evaluate policy rules
        is_dm = not is_group
        is_reply_to_bot = self._is_reply_to_bot(data, platform)

        context = self.policy_evaluator.create_context(
            chat_id=chat_id,
            sender_id=sender_id,
            text=text,
            is_group=is_group,
            contact=contact,
            group=group,
            is_reply_to_bot=is_reply_to_bot,
            platform=platform,
        )

        decision = self.policy_evaluator.evaluate(context)

        if not decision.should_respond:
            logger.debug(f"Policy decision: no response (reason: {decision.reason})")
            return

        logger.info(f"Responding to message (policy: {decision.reason}, action: {decision.action.value})")

        # 6. Generate response with role-based prompt
        response = await self._generate_response(chat_id, data, contact)

        if not response:
            logger.warning("Failed to generate response")
            return

        # 7. Send response via transport
        if self._send_message:
            success = await self._send_message(platform, chat_id, response)
            if not success:
                logger.error(f"Failed to send message via {platform}")
                return
        else:
            logger.error("No message sender configured")
            return

        # 8. Update safety trackers
        self.rate_limiter.record_reply()
        self.cooldown.record_reply(chat_id)

        # 9. Store our response
        self_id = self.self_ids.get(platform, "self")
        bot_message = Message(
            id=None,
            chat_id=chat_id,
            sender_id=self_id,
            sender_name=self.bot_name,
            text=response,
            timestamp=time.time(),
            is_self=True,
            platform=platform
        )
        self.store.store_message(bot_message)

        logger.info(f"Response sent via {platform}: {response[:50]}...")

    def _check_safety_rules(self, chat_id: str) -> Optional[str]:
        """
        Check all safety rules.

        Returns:
            Reason string if should skip, None if OK to proceed
        """
        # Check quiet hours
        if self.quiet_hours.is_quiet_time():
            return "quiet_hours"

        # Check rate limit
        if not self.rate_limiter.can_reply():
            return "rate_limit"

        # Check per-chat cooldown
        if self.cooldown.is_on_cooldown(chat_id):
            return "cooldown"

        # Check double-reply (don't reply if last message was ours)
        if self.store.was_last_message_from_self(chat_id):
            return "double_reply"

        return None

    def _is_reply_to_bot(self, data: Dict[str, Any], platform: str = "whatsapp") -> bool:
        """Check if the message is a reply to one of our messages."""
        quoted = data.get('quotedMessage')
        if not quoted:
            return False

        quoted_sender = quoted.get('senderId', '')

        # Check if quoted message is from us (platform-specific self ID)
        self_id = self.self_ids.get(platform)
        if self_id and quoted_sender == self_id:
            return True

        # Also check for our name in the quoted sender
        if self.bot_name.lower() in quoted_sender.lower():
            return True

        return False

    async def _generate_response(
        self,
        chat_id: str,
        message_data: Dict[str, Any],
        contact: Optional[ContactProfile] = None
    ) -> Optional[str]:
        """Generate an LLM response for the message."""
        # Build context
        context = self.context_builder.build_context(chat_id, message_data)

        # Detect language
        text = message_data.get('text', '')
        language = self.context_builder.detect_language(text)
        language_instruction = self.context_builder.get_language_instruction(language)

        logger.debug(f"Detected language: {language}")

        # Build role-based system prompt
        if contact:
            system_prompt = self.prompt_builder.build_prompt(
                tone=contact.tone,
                contact_name=contact.name if contact.name != "Unknown" else None,
            )
            logger.debug(f"Using tone: {contact.tone.value} for {contact.name}")
        else:
            system_prompt = get_personality_prompt(self.bot_name)

        # Generate response
        response = await self.llm.generate_response(
            system_prompt=system_prompt,
            messages=context,
            language_instruction=language_instruction
        )

        return response
