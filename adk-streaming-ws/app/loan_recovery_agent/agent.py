from google.adk.agents import Agent

from .config import GEMINI_MODEL  # Validates all env vars on import
from .sub_agents import initiate_conversation, read_profile
from .prompts import MANAGER_INSTRUCTION
from .descriptions import MANAGER_DESCRIPTION

root_agent = Agent(
    model=GEMINI_MODEL,
    name="manager",
    description=MANAGER_DESCRIPTION,
    instruction=MANAGER_INSTRUCTION,
    sub_agents=[
        read_profile,
        initiate_conversation,
    ]
)