from google.adk.agents import Agent

from ..config import GEMINI_MODEL
from ..prompts import SENIOR_MANAGER_INSTRUCTION
from ..descriptions import SENIOR_MANAGER_DESCRIPTION


senior_manager = Agent(
    model=GEMINI_MODEL,
    name="senior_manager",
    description=SENIOR_MANAGER_DESCRIPTION,
    instruction=SENIOR_MANAGER_INSTRUCTION,
)



