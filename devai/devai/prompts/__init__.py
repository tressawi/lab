"""Prompt templates for agents"""

from .system import DEV_SYSTEM_PROMPT
from .tasks import FEATURE_TEMPLATE, BUGFIX_TEMPLATE, REFACTOR_TEMPLATE

__all__ = [
    "DEV_SYSTEM_PROMPT",
    "FEATURE_TEMPLATE",
    "BUGFIX_TEMPLATE",
    "REFACTOR_TEMPLATE",
]
