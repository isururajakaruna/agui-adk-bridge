#!/bin/bash

# ADK Bridge Run Script
# This script starts the AG-UI Dojo to Agent Engine Bridge

set -e  # Exit on error

echo "🚀 AG-UI Dojo ADK Bridge - Starting Application"
echo "==============================================="
echo ""

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ]; then
    echo "❌ Error: pyproject.toml not found. Please run this script from the agui-dojo-adk-bridge directory."
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "⚠️  Virtual environment not found. Running setup..."
    echo ""
    ./setup.sh
    echo ""
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "❌ Error: .env file not found!"
    echo "   Please create .env with your GCP credentials."
    echo "   Run: cp .env.example .env (if exists) or ./setup.sh"
    exit 1
fi

# Validate .env has required fields
if ! grep -q "GCP_PROJECT_ID=your-project-id" .env; then
    echo "✅ .env appears to be configured"
else
    echo "⚠️  Warning: .env may not be properly configured!"
    echo "   Please edit .env with your GCP credentials:"
    echo "   - GCP_PROJECT_ID"
    echo "   - GCP_LOCATION"
    echo "   - AGENT_ENGINE_RESOURCE_ID"
    echo ""
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ Aborted"
        exit 1
    fi
fi

# Check if port 8000 is already in use
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "⚠️  Port 8000 is already in use. Killing existing process..."
    lsof -ti:8000 | xargs kill -9 2>/dev/null || true
    sleep 1
fi

# Check Google Cloud authentication
echo "🔐 Checking Google Cloud authentication..."
if gcloud auth application-default print-access-token >/dev/null 2>&1; then
    echo "✅ Google Cloud authenticated"
else
    echo "⚠️  Google Cloud not authenticated!"
    echo "   Run: gcloud auth application-default login"
    echo ""
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ Aborted"
        echo "   Please run: gcloud auth application-default login"
        exit 1
    fi
fi

echo ""
echo "🌐 Starting bridge on http://localhost:8000"
echo "📡 Connecting to Google Agent Engine"
echo ""
echo "📝 Logs will be saved to: logs/events_*.log"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Activate virtual environment
source venv/bin/activate

# Load environment variables
export $(grep -v '^#' .env | xargs)

# Start the bridge (use -m to run as module, fixing relative imports)
python -m src.main

