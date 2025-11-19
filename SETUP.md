# 🚀 AG-UI Dojo ADK Bridge - Setup Guide

Quick setup and run instructions for the ADK Bridge connecting AG-UI Dojo to Google Agent Engine.

## 📋 Prerequisites

- **Python 3.9-3.13** ([Download](https://www.python.org/))
- **Google Cloud SDK** (`gcloud` CLI) ([Install](https://cloud.google.com/sdk/docs/install))
- **Google Cloud Project** with Agent Engine deployed
- **pip** (Python package manager)

---

## ⚡ Quick Start

### 1️⃣ First Time Setup

```bash
cd /path/to/agui-dojo-adk-bridge
./setup.sh
```

This will:
- ✅ Check Python version (3.9-3.13 required)
- ✅ Create Python virtual environment (`venv/`)
- ✅ Install all dependencies from `pyproject.toml`
- ✅ Create `.env` template file

### 2️⃣ Configure Environment

Edit `.env` with your Google Cloud credentials:

```bash
nano .env
```

Required fields:
```bash
GCP_PROJECT_ID=your-project-id              # Your GCP project ID
GCP_LOCATION=us-central1                    # Agent Engine location
AGENT_ENGINE_RESOURCE_ID=your-resource-id   # Agent Engine resource ID
```

### 3️⃣ Authenticate with Google Cloud

```bash
gcloud auth application-default login
```

### 4️⃣ Run the Bridge

```bash
./run.sh
```

This will:
- ✅ Check virtual environment and dependencies
- ✅ Validate `.env` configuration
- ✅ Verify Google Cloud authentication
- ✅ Start bridge on http://localhost:8000
- ✅ Create event logs in `logs/` directory

---

## 🔧 Manual Setup (if needed)

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -e .

# Load environment variables
export $(grep -v '^#' .env | xargs)

# Start the bridge
python src/main.py
```

---

## 🌐 Access Points

- **Bridge API**: http://localhost:8000
- **Health Check**: http://localhost:8000/health
- **API Docs**: http://localhost:8000/docs
- **Chat Endpoint**: http://localhost:8000/chat (POST)

---

## 🛠️ Configuration

### `.env` File

```bash
# Google Cloud Configuration
GCP_PROJECT_ID=your-project-id
GCP_LOCATION=us-central1
AGENT_ENGINE_RESOURCE_ID=your-resource-id

# Optional: Service Account
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
```

---

## 🐛 Troubleshooting

### Python version issues
```bash
# Check Python version
python3 --version  # Should be 3.9-3.13

# Use specific Python version
python3.11 -m venv venv
```

### Google Cloud authentication failed
```bash
# Re-authenticate
gcloud auth application-default login

# Check authentication
gcloud auth application-default print-access-token
```

### Port 8000 already in use
```bash
# Kill existing process
lsof -ti:8000 | xargs kill -9
```

### Dependencies issues
```bash
# Clean reinstall
rm -rf venv
./setup.sh
```

### Agent Engine connection failed
- ✅ Check `GCP_PROJECT_ID` in `.env`
- ✅ Check `GCP_LOCATION` in `.env`
- ✅ Check `AGENT_ENGINE_RESOURCE_ID` in `.env`
- ✅ Verify Agent Engine is deployed in GCP
- ✅ Check Google Cloud authentication

---

## 📂 Project Structure

```
agui-dojo-adk-bridge/
├── setup.sh              ← Setup script
├── run.sh                ← Run script
├── SETUP.md              ← This file
├── README.md             ← Full documentation
├── .env                  ← Configuration (create from template)
├── .env.example          ← Template
├── pyproject.toml        ← Python dependencies
├── requirements.txt      ← Pip requirements
├── venv/                 ← Virtual environment (auto-created)
├── logs/                 ← Event logs (auto-created)
│   └── events_*.log      ← Timestamped logs
├── src/
│   ├── main.py           ← FastAPI application
│   ├── config.py         ← Configuration loader
│   └── agent_engine_client.py  ← Reasoning Engine client
└── reference/            ← Reference implementations
```

---

## 📝 Event Logs

Logs are automatically saved to `logs/events_YYYYMMDD_HHMMSS.log`

View logs in real-time:
```bash
tail -f logs/events_*.log
```

Search for specific events:
```bash
grep "TOOL_CALL" logs/events_*.log
grep "thought_signature" logs/events_*.log
```

---

## 🎯 Features

- ✅ **FastAPI Bridge** - RESTful API for AG-UI Protocol
- ✅ **Reasoning Engine Client** - Direct connection to Vertex AI
- ✅ **SSE Streaming** - Real-time event streaming
- ✅ **Event Translation** - ADK ↔ AG-UI Protocol
- ✅ **Comprehensive Logging** - Debug-level event logs
- ✅ **Google Cloud Auth** - Application Default Credentials
- ✅ **Error Handling** - Graceful error responses
- ✅ **Environment Config** - `.env` based configuration

---

## 🔐 Authentication Methods

### 1. Application Default Credentials (Recommended)
```bash
gcloud auth application-default login
```

### 2. Service Account Key
```bash
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/key.json"
```

### 3. API Key
```bash
# In .env
GOOGLE_API_KEY=your-api-key
```

---

## 🆘 Need Help?

1. Check bridge is running: `curl http://localhost:8000/health`
2. Check server logs in `logs/` directory
3. Check terminal output for errors
4. Review `README.md` for detailed documentation
5. Verify Google Cloud authentication
6. Check Agent Engine deployment status

---

## 📚 Dependencies

Main packages (from `pyproject.toml`):
- `fastapi>=0.104.0` - Web framework
- `uvicorn[standard]>=0.24.0` - ASGI server
- `ag_ui_adk>=0.1.0` - AG-UI Protocol middleware
- `google-cloud-aiplatform>=1.60.0` - GCP AI Platform
- `google-auth>=2.0.0` - Google authentication
- `httpx>=0.27.0` - Async HTTP client
- `python-dotenv>=1.0.0` - Environment variables
- `pydantic>=2.0.0` - Data validation

---

## 🔗 Related Projects

- **Agent Testing UI**: Frontend application (port 3005)
- **AG-UI Protocol**: https://github.com/ag-ui
- **Google ADK**: https://cloud.google.com/vertex-ai/generative-ai/docs/reasoning-engine

---

**Built with FastAPI, Google ADK, and AG-UI Protocol** 🚀

