# ADK Streaming WebSocket Application

A bidirectional streaming application built with Google ADK (Agent Development Kit) supporting multiple AI agents for different use cases.

## ✨ Features

- **Bidirectional Streaming**: Real-time WebSocket communication with AI agents
- **Multi-Agent Support**: Switch between different agents based on your needs
- **Text & Voice Modes**: Support for both text chat and voice conversations
- **Enhanced Web UI**: Modern interface with comprehensive status tracking
  - 📊 **Real-time status indicators** - Know exactly what's happening
  - 🎤 **Live speech recognition** - See what you're saying as you speak
  - ⏱️ **Timing information** - Track performance of each step
  - 🎨 **Beautiful design** - Gradient theme with clear visual feedback
  - 📱 **Mobile responsive** - Works on all devices

## 🤖 Available Agents

### 1. Loan Recovery Agent (Default)
A sophisticated multi-agent system for automated loan recovery conversations:

- **Manager Agent**: Orchestrates the complete workflow
- **Read Profile Agent**: Reads and searches customer data from CSV files
- **Junior Executive Agent**: Conducts initial recovery conversations
- **Senior Manager Agent**: Handles payment plan modifications and escalations

**Features**:
- Automatic customer data loading from CSV
- 40 sample customers with 19 defaulters included
- Smart escalation workflow
- Configurable prompts and descriptions
- Voice-friendly short responses

### 2. Google Search Agent
An agent with Google Search capabilities for answering questions using web search.

## 🚀 Quick Start

### Prerequisites
- Python 3.x
- Virtual environment already set up with required packages

### Starting the Application

**Option 1: Using the startup script (Recommended)**
```bash
cd /home/shtlp_0079/Documents/budu2/adk-streaming-ws
./start.sh
```

**Option 2: Manual start**
```bash
cd /home/shtlp_0079/Documents/budu2/adk-streaming-ws
source venv/bin/activate
cd app
uvicorn main:app --reload
```

### Accessing the Application
Open your browser and navigate to: **http://127.0.0.1:8000**

## 🔧 Configuration

### Switching Between Agents

Set the `ACTIVE_AGENT` environment variable before starting:

```bash
# Use Loan Recovery Agent (default)
export ACTIVE_AGENT=loan_recovery
./start.sh

# Use Google Search Agent
export ACTIVE_AGENT=google_search
./start.sh
```

### Environment Variables

Create a `.env` file in the project root (optional):

```env
# Active agent selection
ACTIVE_AGENT=loan_recovery

# Loan Recovery Agent settings
GEMINI_MODEL=gemini-2.0-flash-exp
CUSTOMER_DATA_FILE=/path/to/your/customer_data.csv

# Google API configuration (if needed)
GOOGLE_API_KEY=your_api_key_here
GOOGLE_GENAI_USE_VERTEXAI=false
```

**Note**: All settings have sensible defaults. No configuration required for testing!

## 📋 Using the Loan Recovery Agent

### Workflow

1. **Start Conversation**: Send any greeting (e.g., "hi", "hello")
2. **Provide Customer Name**: When asked, enter a customer name
3. **Recovery Conversation**: Engage with the junior executive
4. **Escalation** (if needed): System automatically escalates to senior manager for payment plan modifications

### Sample Customers

The application includes a sample dataset with these customers:

- **Sneha Reddy** - Car Loan, ₹800,000, 90 days overdue
- **Rajesh Kumar** - Personal Loan defaulter
- **Priya Sharma** - Business Loan defaulter
- **Amit Patel** - Home Loan defaulter
- **Vikram Singh** - Car Loan defaulter
- ...and 35 more customers (19 defaulters total)

### Creating Your Own Dataset

To use your own customer data:

1. Create a CSV file with required columns:
   - Customer_ID, Name, Phone, Email, Status
   - Loan_Type, Loan_Amount, EMI_Amount, Days_Overdue
   - (See `app/loan_recovery_agent/README.md` for full column list)

2. Set the path:
   ```bash
   export CUSTOMER_DATA_FILE=/path/to/your/data.csv
   ```

3. Restart the application

## 📁 Project Structure

```
adk-streaming-ws/
├── README.md                      # This file
├── AGENT_INTEGRATION.md          # Detailed integration guide
├── start.sh                      # Quick start script
├── app/
│   ├── main.py                   # Main FastAPI application
│   ├── requirements.txt          # Python dependencies
│   ├── loan_recovery_agent/      # Loan Recovery Agent
│   │   ├── agent.py              # Root manager agent
│   │   ├── config.py             # Configuration management
│   │   ├── sub_agents/           # Sub-agent implementations
│   │   │   ├── read_profile.py
│   │   │   ├── initiate_conversation.py
│   │   │   └── senior_manager.py
│   │   ├── prompts/              # Agent instruction prompts
│   │   ├── descriptions/         # Agent descriptions
│   │   ├── assets/               # Sample customer dataset
│   │   │   └── loan_customers_dataset.csv
│   │   └── README.md             # Agent-specific documentation
│   ├── google_search_agent/      # Google Search Agent
│   │   └── agent.py
│   └── static/                   # Web UI files
│       ├── index.html
│       └── js/
└── venv/                         # Virtual environment
```

## 🎯 Key Features

### Bidirectional Streaming
- Real-time WebSocket communication
- Supports both text and audio modes
- Streaming responses from AI agents
- Session resumption for reliability

### Multi-Agent Architecture
- Manager orchestrates sub-agents
- Automatic workflow progression
- Smart delegation between agents
- Context maintained throughout conversation

### Voice Support
- Audio input via microphone
- Audio output for agent responses
- PCM audio format
- Real-time transcription

## 🔍 Troubleshooting

### Server won't start
- Check if port 8000 is already in use
- Ensure virtual environment is activated
- Verify all dependencies are installed

### Agent errors
- Check the model name is correct (should be gemini-2.0-flash-exp or similar)
- Ensure API keys are set if required
- Check logs in terminal for specific errors

### Customer not found
- Verify the customer name spelling
- Check the CSV file path is correct
- Ensure the CSV has the required columns
- Try with sample customers first

## 📚 Documentation

- **Agent Integration Guide**: See `AGENT_INTEGRATION.md`
- **Loan Recovery Agent**: See `app/loan_recovery_agent/README.md`
- **API Documentation**: Available at http://127.0.0.1:8000/docs when server is running

## 🛠️ Development

### Adding New Agents

1. Create agent folder in `app/` directory
2. Implement agent.py with root_agent
3. Update main.py to import your agent
4. Add agent selection logic in main.py

### Customizing Prompts

Edit the prompt files in `app/loan_recovery_agent/prompts/` to customize agent behavior.

### Customizing Descriptions

Edit the description files in `app/loan_recovery_agent/descriptions/` to update agent descriptions.

## 📊 Sample Dataset

The included dataset (`loan_customers_dataset.csv`) contains:
- **40 total customers**
- **19 defaulters** (Status = "Defaulter")
- **21 paid customers** (Status = "Paid")
- Complete loan information (type, amount, EMI, overdue days)
- Customer demographics and contact information
- Recovery strategy fields (temperament, financial situation, willingness to pay)

## 🎤 Voice Mode Tips

When using voice mode:
- Speak clearly and wait for the agent to finish
- **Watch "What You're Saying" panel** - see your speech in real-time!
- Agent responses are kept short (2-3 sentences) for better UX
- You can see transcripts in the UI
- Audio quality depends on your microphone
- Status indicators show when you're being heard

## 📊 UI Features

### Real-Time Status Tracking
The interface shows 5 status indicators:
- 🔵 **Idle** - Ready for input
- 🎤 **Listening** - Capturing your voice
- 📤 **Sending** - Transmitting your message
- ⚙️ **Processing** - Agent is thinking
- 💬 **Responding** - Agent is replying

**Active status pulses with visual animation!**

### Speech Recognition Display
See what you're saying as you speak:
- Real-time transcription in "What You're Saying" panel
- Visual border highlight when listening
- Immediate confirmation your voice is being captured
- Works automatically in voice mode

### Timing Information
Track performance metrics:
- **Last Input**: Time to capture/send your message
- **Processing**: How long agent takes to start responding
- **Response**: Duration of agent's response
- **Total**: Complete conversation turn time

All times displayed in seconds with precision.

### Visual Feedback
- Connection status indicator (green when connected)
- Clear separation of user vs agent messages
- System notifications for important events
- Mobile-responsive design

**For detailed UI documentation, see: `UI_ENHANCEMENTS.md`**

## 🔐 Security Notes

- Keep your API keys secure (never commit to version control)
- Use environment variables or .env files for sensitive data
- The .env file is gitignored by default

## 📞 Support

For issues or questions:
1. Check the troubleshooting section
2. Review the logs in the terminal
3. Consult the detailed documentation files

## 🎉 Success!

Your loan recovery agent is now integrated and ready for bidirectional streaming!

Test it out:
1. Start the server with `./start.sh`
2. Open http://127.0.0.1:8000
3. Try text or voice mode
4. Ask to process "Sneha Reddy" as a test customer
5. Experience the multi-agent workflow!

