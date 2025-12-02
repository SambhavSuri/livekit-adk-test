# Loan Recovery Agent

A multi-agent system for automated loan recovery conversations using Google ADK.

## Architecture

The system consists of three agents:

1. **Manager Agent** (`agent.py`) - Orchestrates the workflow
2. **Read Profile Agent** (`sub_agents/read_profile.py`) - Reads customer data from CSV/Excel
3. **Initiate Conversation Agent** (`sub_agents/initiate_conversation.py`) - Conducts recovery conversations

## Configuration

### Environment Variables

Configure the system using environment variables. A template file `env.example` is provided at the project root (`contact_center_bot/env.example`).

**Setup:**
1. Copy the example file: `cp env.example .env`
2. Edit `.env` with your values
3. The application will automatically load these variables

**Required Variables:**

```bash
# Gemini Model Selection
GEMINI_MODEL=gemini-2.0-flash-exp

# Google GenAI Configuration
GOOGLE_GENAI_USE_VERTEXAI=false  # Set to "true" for Vertex AI

# Google API Key (required for Google AI Studio)
GOOGLE_API_KEY=your_api_key_here

# Customer Data File Path (automatically loaded on startup)
CUSTOMER_DATA_FILE=/path/to/your/loan_customers_dataset.csv
```



**Important Notes:**
- ⚠️ **GEMINI_MODEL is REQUIRED** - The application will fail if this is not set in your .env file
- ⚠️ **CUSTOMER_DATA_FILE is REQUIRED** - Path to your customer data CSV file
- Get your API key from: https://makersuite.google.com/app/apikey
- Required when using Google AI Studio (`GOOGLE_GENAI_USE_VERTEXAI=false`)

### Prompt Customization

Agent prompts and descriptions are organized in dedicated folders for easy maintenance:

**Instruction Prompts** (`prompts/` folder):
- `prompts/manager_prompt.py` - Manager agent instruction
- `prompts/read_profile_prompt.py` - Read profile agent instruction
- `prompts/initiate_conversation_prompt.py` - Initiate conversation agent instruction

**Agent Descriptions** (`descriptions/` folder):
- `descriptions/manager_description.py` - Manager agent description
- `descriptions/read_profile_description.py` - Read profile agent description
- `descriptions/initiate_conversation_description.py` - Initiate conversation agent description

Both folders include `__init__.py` files that export all prompts/descriptions for easy importing.

## Usage

### Run with ADK Web Interface

```bash
cd contact_center_bot/contact_center_bot/loan_recovery_agent
poetry run adk web
```

### Run with Custom Model

```bash
export GEMINI_MODEL="gemini-2.5-flash"
poetry run adk web
```

### Import in Code

```python
from loan_recovery_agent.agent import root_agent

# Use the root_agent in your application
```

## Customer Data Format

The system expects CSV/Excel files with the following columns:

**Required:**
- Customer_ID, Name, Phone, Email
- Status (must be "Defaulter" for recovery)
- Loan_Type, Loan_Amount, EMI_Amount
- Days_Overdue

**Recommended:**
- Customer_Temperament (Cooperative, Anxious, Defensive, etc.)
- Financial_Situation (Stable, Struggling, etc.)
- Willingness_To_Pay (High, Medium, Low)
- Reason_For_Default
- Best_Call_Time

See `assets/loan_customers_dataset.csv` for a sample dataset.

## Workflow

1. User starts conversation (any first message)
2. Manager automatically delegates to Read Profile agent
3. Read Profile automatically loads file from CUSTOMER_DATA_FILE env var
4. User provides customer name
5. Read Profile searches for customer and validates defaulter status
6. Manager automatically delegates to Initiate Conversation agent
7. Conversation agent conducts recovery dialogue
8. System documents outcome

## Project Structure

```
loan_recovery_agent/
├── prompts/              # All agent instruction prompts
│   ├── __init__.py
│   ├── manager_prompt.py
│   ├── read_profile_prompt.py
│   └── initiate_conversation_prompt.py
├── descriptions/         # All agent descriptions
│   ├── __init__.py
│   ├── manager_description.py
│   ├── read_profile_description.py
│   └── initiate_conversation_description.py
├── sub_agents/          # Agent implementations
│   ├── __init__.py
│   ├── read_profile.py
│   └── initiate_conversation.py
├── assets/              # Data files
│   └── loan_customers_dataset.csv
├── agent.py             # Root manager agent
└── README.md
```

## Development

### Modifying Prompts

Edit the corresponding files in the `prompts/` folder to customize agent behavior. No need to restart - changes take effect on next agent initialization.

### Modifying Descriptions

Edit the corresponding files in the `descriptions/` folder to update agent descriptions shown in the UI.

### Adding Tools

Add new tools to the relevant agent file:

```python
def my_new_tool(param: str) -> dict:
    """Tool description"""
    # Implementation
    return {"result": "success"}

# Add to agent
agent = Agent(
    tools=[existing_tool, my_new_tool],
    ...
)
```

