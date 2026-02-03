"""Configuration module."""

from .settings import Settings
from .personality import SYSTEM_PROMPT, get_personality_prompt

__all__ = ['Settings', 'SYSTEM_PROMPT', 'get_personality_prompt']
