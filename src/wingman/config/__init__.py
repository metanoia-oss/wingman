"""Configuration module for Wingman."""

from .paths import WingmanPaths
from .personality import SYSTEM_PROMPT, RoleBasedPromptBuilder, get_personality_prompt
from .registry import (
    ContactProfile,
    ContactRegistry,
    ContactRole,
    ContactTone,
    GroupCategory,
    GroupConfig,
    GroupRegistry,
    ReplyPolicy,
)
from .settings import Settings

__all__ = [
    "Settings",
    "WingmanPaths",
    "SYSTEM_PROMPT",
    "get_personality_prompt",
    "RoleBasedPromptBuilder",
    "ContactRegistry",
    "GroupRegistry",
    "ContactProfile",
    "GroupConfig",
    "ContactRole",
    "ContactTone",
    "GroupCategory",
    "ReplyPolicy",
]
