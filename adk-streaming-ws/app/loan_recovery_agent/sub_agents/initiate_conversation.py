from google.adk.agents import Agent
from google.adk.tools.tool_context import ToolContext

from ..config import GEMINI_MODEL
from ..prompts import INITIATE_CONVERSATION_INSTRUCTION
from ..descriptions import INITIATE_CONVERSATION_DESCRIPTION

initiate_conversation = Agent(
    model=GEMINI_MODEL,
    name="initiate_conversation",
    description=INITIATE_CONVERSATION_DESCRIPTION,
    instruction=INITIATE_CONVERSATION_INSTRUCTION,
)