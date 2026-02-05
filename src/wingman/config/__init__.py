"""Configuration module for Wingman."""

from .settings import Settings
from .paths import WingmanPaths
from .personality import SYSTEM_PROMPT, get_personality_prompt, RoleBasedPromptBuilder
from .registry import (
    ContactRegistry,
    GroupRegistry,
    ContactProfile,
    GroupConfig,
    ContactRole,
    ContactTone,
    GroupCategory,
    ReplyPolicy,
)

__all__ = [
    'Settings',
    'WingmanPaths',
    'SYSTEM_PROMPT',
    'get_personality_prompt',
    'RoleBasedPromptBuilder',
    'ContactRegistry',
    'GroupRegistry',
    'ContactProfile',
    'GroupConfig',
    'ContactRole',
    'ContactTone',
    'GroupCategory',
    'ReplyPolicy',
]
