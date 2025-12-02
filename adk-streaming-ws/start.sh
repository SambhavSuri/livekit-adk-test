#!/bin/bash
# Startup script for ADK Streaming WebSocket Application

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Starting ADK Streaming WebSocket Application${NC}"
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}⚠️  Virtual environment not found. Please run: python3 -m venv venv${NC}"
    exit 1
fi

# Activate virtual environment
echo -e "${GREEN}📦 Activating virtual environment...${NC}"
source venv/bin/activate

# Check which agent to use
AGENT="${ACTIVE_AGENT:-loan_recovery}"
echo -e "${GREEN}🎯 Active Agent: ${AGENT}${NC}"
echo ""

if [ "$AGENT" = "loan_recovery" ]; then
    echo -e "${BLUE}📋 Loan Recovery Agent Configuration:${NC}"
    echo "   - Multi-agent system for loan recovery conversations"
    echo "   - Includes Manager, Read Profile, Junior Executive, and Senior Manager agents"
    echo "   - Sample dataset included with 40 customers (19 defaulters)"
    echo ""
    echo -e "${YELLOW}💡 Sample customer names to try:${NC}"
    echo "   - Sneha Reddy"
    echo "   - Rajesh Kumar"
    echo "   - Priya Sharma"
    echo "   - Amit Patel"
    echo ""
elif [ "$AGENT" = "google_search" ]; then
    echo -e "${BLUE}🔍 Google Search Agent Configuration:${NC}"
    echo "   - Agent with Google Search capabilities"
    echo "   - Ask questions and get answers from Google Search"
    echo ""
fi

# Navigate to app directory and start server
echo -e "${GREEN}🌐 Starting uvicorn server...${NC}"
echo -e "${BLUE}📱 Open http://127.0.0.1:8000 in your browser${NC}"
echo ""

cd app
uvicorn main:app --reload

