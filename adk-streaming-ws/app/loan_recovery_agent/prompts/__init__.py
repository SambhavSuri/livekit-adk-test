"""
Agent Instruction Prompts

This module contains all agent instruction prompts for the loan recovery system.
"""

from .manager_prompt import MANAGER_INSTRUCTION
from .read_profile_prompt import READ_PROFILE_INSTRUCTION
from .initiate_conversation_prompt import INITIATE_CONVERSATION_INSTRUCTION
from .senior_manager_prompt import SENIOR_MANAGER_INSTRUCTION

__all__ = [
    "MANAGER_INSTRUCTION",
    "READ_PROFILE_INSTRUCTION",
    "INITIATE_CONVERSATION_INSTRUCTION",
    "SENIOR_MANAGER_INSTRUCTION",
]







