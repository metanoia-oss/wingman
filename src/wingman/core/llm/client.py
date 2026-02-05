"""OpenAI API client wrapper."""

import logging

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


class LLMClient:
    """Async OpenAI API client for generating responses."""

    def __init__(
        self, api_key: str, model: str = "gpt-4o", max_tokens: int = 150, temperature: float = 0.8
    ):
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature

    async def generate_response(
        self,
        system_prompt: str,
        messages: list[dict[str, str]],
        language_instruction: str | None = None,
    ) -> str | None:
        """
        Generate a response using the OpenAI API.

        Args:
            system_prompt: The personality/system prompt
            messages: Conversation history
            language_instruction: Optional language-specific instruction

        Returns:
            Generated response text or None on error
        """
        try:
            # Build full system prompt
            full_system = system_prompt
            if language_instruction:
                full_system += f"\n\n{language_instruction}"

            # Prepare messages for API
            api_messages = [{"role": "system", "content": full_system}, *messages]

            logger.debug(f"Sending request to {self.model} with {len(messages)} context messages")

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=api_messages,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
            )

            if response.choices and response.choices[0].message.content:
                text = response.choices[0].message.content.strip()
                logger.debug(f"Generated response: {text[:50]}...")
                return text

            logger.warning("Empty response from API")
            return None

        except Exception as e:
            logger.error(f"API error: {e}")
            return None

    async def health_check(self) -> bool:
        """Check if the API is accessible."""
        try:
            response = await self.client.chat.completions.create(
                model=self.model, messages=[{"role": "user", "content": "Hi"}], max_tokens=5
            )
            return bool(response.choices)
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
