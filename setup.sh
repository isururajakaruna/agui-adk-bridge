#!/bin/bash

# ADK Bridge Setup Script
# This script sets up the AG-UI Dojo to Agent Engine Bridge

set -e  # Exit on error

echo "🚀 AG-UI Dojo ADK Bridge - Setup Script"
echo "======================================="
echo ""

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ]; then
    echo "❌ Error: pyproject.toml not found. Please run this script from the agui-dojo-adk-bridge directory."
    exit 1
fi

# Check for Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is not installed."
    echo "   Please install Python 3.9+ from https://www.python.org/"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | awk '{print $2}' | cut -d'.' -f1,2)
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d'.' -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d'.' -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 9 ]); then
    echo "❌ Error: Python version must be 3.9 or higher (current: $(python3 --version))"
    exit 1
fi

echo "✅ Python version: $(python3 --version)"

# Check for pip
if ! command -v pip3 &> /dev/null; then
    echo "❌ Error: pip3 is not installed."
    exit 1
fi

echo "✅ pip version: $(pip3 --version)"
echo ""

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found. Creating template..."
    cat > .env << 'EOF'
# Google Cloud Configuration
# Get these from your Agent Engine deployment
GCP_PROJECT_ID=your-project-id
GCP_LOCATION=us-central1
AGENT_ENGINE_RESOURCE_ID=your-agent-resource-id

# Optional: Service Account for authentication
# GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json

# Or use API Key
# GOOGLE_API_KEY=your-api-key

# Server Configuration
PORT=8000
HOST=0.0.0.0

# ADK Middleware Configuration
APP_NAME=dojo_bridge
SESSION_TIMEOUT_SECONDS=1200
EXECUTION_TIMEOUT_SECONDS=600
MAX_CONCURRENT_EXECUTIONS=10

# Environment
ENVIRONMENT=development
EOF
    echo "⚠️  Created .env template - Please edit it with your GCP credentials!"
    echo "   Edit: nano .env"
    echo ""
else
    echo "✅ .env file exists"
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating Python virtual environment..."
    python3 -m venv venv
    echo "✅ Created virtual environment"
else
    echo "✅ Virtual environment already exists"
fi

echo ""
echo "📦 Installing dependencies..."
echo "   This may take a few minutes..."
echo ""

# Activate virtual environment and install dependencies
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip > /dev/null 2>&1

# Install dependencies from pyproject.toml
pip install -e .

echo ""
echo "✅ Setup complete!"
echo ""
echo "⚠️  IMPORTANT: Before running, make sure to:"
echo "   1. Edit .env with your GCP credentials:"
echo "      - GCP_PROJECT_ID"
echo "      - GCP_LOCATION"
echo "      - AGENT_ENGINE_RESOURCE_ID"
echo "   2. Authenticate with Google Cloud:"
echo "      gcloud auth application-default login"
echo ""
echo "📋 Next Steps:"
echo "   1. Edit .env: nano .env"
echo "   2. Authenticate: gcloud auth application-default login"
echo "   3. Run the bridge: ./run.sh"
echo ""
