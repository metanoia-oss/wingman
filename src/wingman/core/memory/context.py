"""Context building for LLM conversations."""

import logging
from typing import Any

from .models import MessageStore

logger = logging.getLogger(__name__)


class ContextBuilder:
    """Builds conversation context for LLM from stored messages."""

    def __init__(
        self,
        message_store: MessageStore,
        window_size: int = 30,
        bot_name: str = "Maximus"
    ):
        self.store = message_store
        self.window_size = window_size
        self.bot_name = bot_name

    def build_context(
        self,
        chat_id: str,
        current_message: dict[str, Any]
    ) -> list[dict[str, str]]:
        """
        Build conversation context for the LLM.

        Args:
            chat_id: Chat to build context for
            current_message: The current incoming message

        Returns:
            List of message dicts for OpenAI API format
        """
        # Get recent messages from storage
        messages = self.store.get_recent_messages(
            chat_id,
            limit=self.window_size
        )

        # Convert to OpenAI message format
        context = []
        for msg in messages:
            if msg.is_self:
                context.append({
                    "role": "assistant",
                    "content": msg.text
                })
            else:
                # Format user messages with sender name for context
                sender = msg.sender_name or "User"
                content = f"[{sender}]: {msg.text}"
                context.append({
                    "role": "user",
                    "content": content
                })

        # Add current message
        sender_name = current_message.get('senderName') or "User"
        context.append({
            "role": "user",
            "content": f"[{sender_name}]: {current_message.get('text', '')}"
        })

        logger.debug(f"Built context with {len(context)} messages for {chat_id}")
        return context

    def detect_language(self, text: str) -> str:
        """
        Detect the primary language of the text.
        Simple heuristic for Hindi/Hinglish/English detection.

        Returns:
            'hindi', 'hinglish', or 'english'
        """
        # Devanagari Unicode range
        hindi_chars = sum(1 for c in text if '\u0900' <= c <= '\u097F')

        if hindi_chars > len(text) * 0.3:
            return 'hindi'

        # Check for common Hinglish words/patterns
        hinglish_markers = [
            'hai', 'hain', 'kya', 'nahi', 'aur', 'bhi',
            'kaise', 'kaisa', 'accha', 'theek', 'yaar',
            'bhai', 'arre', 'haan', 'matlab', 'wala',
            'kar', 'karo', 'karna', 'raha', 'rahi'
        ]

        text_lower = text.lower()
        hinglish_count = sum(1 for word in hinglish_markers if word in text_lower)

        if hinglish_count >= 2:
            return 'hinglish'

        return 'english'

    def get_language_instruction(self, language: str) -> str:
        """Get language-specific instruction for the LLM."""
        instructions = {
            'hindi': "Respond in Hindi (Devanagari script). Match the casual tone.",
            'hinglish': "Respond in Hinglish (Hindi words in Roman script mixed with English). Keep it natural and casual.",
            'english': "Respond in English. Keep it casual and friendly."
        }
        return instructions.get(language, instructions['english'])
