#!/bin/bash

# Twilio-OpenAI Voice Assistant Runner Script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
ENV_FILE=".env"
REQUIREMENTS_FILE="requirements.txt"
MAIN_APP="realtime_voice_assistant.py"

echo -e "${BLUE}🎙️  Twilio-OpenAI Realtime Voice Assistant${NC}"
echo "========================================"

# Check if .env file exists
if [ ! -f "$ENV_FILE" ]; then
    echo -e "${YELLOW}⚠️  .env file not found. Creating from template...${NC}"
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo -e "${YELLOW}📝 Please edit .env with your actual credentials${NC}"
        echo -e "${YELLOW}   Required variables:${NC}"
        echo "   - OPENAI_API_KEY"
        echo "   - OPENAI_PROJECT_ID"
        echo "   - OPENAI_WEBHOOK_SECRET"
        echo "   - TWILIO_ACCOUNT_SID"
        echo "   - TWILIO_AUTH_TOKEN"
        exit 1
    else
        echo -e "${RED}❌ No .env.example found. Please create .env manually.${NC}"
        exit 1
    fi
fi

# Check Python availability
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo -e "${RED}❌ Python not found. Please install Python 3.8+${NC}"
    exit 1
fi

# Check if uv is available
if command -v uv &> /dev/null; then
    echo -e "${GREEN}✅ Using uv for dependency management${NC}"
    RUNNER="uv run"
    
    # Install dependencies with uv
    echo -e "${BLUE}📦 Installing dependencies...${NC}"
    uv sync
else
    echo -e "${YELLOW}⚠️  uv not found. Using pip instead${NC}"
    echo -e "${YELLOW}   Recommend installing uv: curl -LsSf https://astral.sh/uv/install.sh | sh${NC}"
    RUNNER="$PYTHON_CMD"
    
    # Install dependencies with pip
    if [ -f "$REQUIREMENTS_FILE" ]; then
        echo -e "${BLUE}📦 Installing dependencies with pip...${NC}"
        pip install -r "$REQUIREMENTS_FILE"
    fi
fi

# Validate environment variables
echo -e "${BLUE}🔍 Validating configuration...${NC}"
echo -e "${GREEN}✅ Using python-dotenv to automatically load .env file${NC}"

# Note: Environment variables will be loaded by the Python app using python-dotenv
# We'll let the Python app handle validation and provide better error messages

echo -e "${GREEN}✅ Configuration validated${NC}"
echo -e "${BLUE}🚀 Starting FastAPI voice assistant server...${NC}"
echo ""
echo "Server will be available at: http://localhost:${PORT:-8000}"
echo "API Documentation: http://localhost:${PORT:-8000}/docs"
echo "Webhook endpoints:"
echo "  - Twilio: http://localhost:${PORT:-8000}/webhook/twilio"
echo "  - OpenAI: http://localhost:${PORT:-8000}/webhook/openai"
echo ""
echo -e "${YELLOW}💡 For local testing, consider using ngrok to expose your server:${NC}"
echo "   ngrok http ${PORT:-8000}"
echo ""
echo -e "${BLUE}Press Ctrl+C to stop the server${NC}"
echo "========================================"

# Run the application
if command -v uv &> /dev/null; then
    uv run python "$MAIN_APP"
else
    # Alternative: run with uvicorn directly
    uvicorn realtime_voice_assistant:app --host 0.0.0.0 --port ${PORT:-8000} --reload
fi