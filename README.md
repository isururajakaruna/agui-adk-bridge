# AG-UI Dojo to Agent Engine Bridge

A bridge service that connects AG-UI Dojo to Google Agent Engine deployments using the ADK middleware.

## Overview

This bridge allows you to use agents deployed on Google's Agent Engine (Vertex AI) with the AG-UI Dojo interface. It translates between:
- **Google Agent Engine** (accessed via project ID and resource ID)
- **AG-UI Protocol** (used by the Dojo interface)

## Architecture

```
┌─────────────────────┐         HTTP/SSE          ┌──────────────────────────┐
│   Dojo (Next.js)    │ ────────────────────────> │   This Bridge App        │
│   localhost:3000    │                           │    localhost:8000        │
└─────────────────────┘                           └──────────────────────────┘
                                                              │
                                                              │ Google Cloud SDK
                                                              ▼
                                                   ┌──────────────────────────┐
                                                   │  Google Agent Engine     │
                                                   │  (Your Deployed Agent)   │
                                                   └──────────────────────────┘
```

## Prerequisites

1. **Python 3.9+** installed
2. **Google Cloud Project** with Agent Engine enabled
3. **Agent deployed** on Google Agent Engine
4. **Authentication** set up (API key or service account)

## Quick Start

### 1. Install Dependencies

Using `uv` (recommended):
```bash
uv sync
```

Or using `pip`:
```bash
pip install -e .
```

### 2. Configure Environment

Copy the example environment file:
```bash
cp .env.example .env
```

Edit `.env` with your Agent Engine details:
```bash
# Required: Your Google Cloud and Agent Engine details
GCP_PROJECT_ID=your-project-id
GCP_LOCATION=us-central1
AGENT_ENGINE_RESOURCE_ID=your-agent-resource-id

# Authentication (choose one)
# Option 1: API Key
GOOGLE_API_KEY=your-api-key

# Option 2: Service Account
# GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json

# Server settings (optional)
PORT=8000
```

### 3. Update Agent Engine Connection

⚠️ **Important**: You need to update `src/agent_engine_client.py` with the correct Google ADK API for connecting to Agent Engine deployments.

Check the [Google ADK documentation](https://google.github.io/adk-docs/) for the proper way to connect to deployed agents.

### 4. Run the Bridge

Development mode (with auto-reload):
```bash
uv run dev
```

Or production mode:
```bash
uv run start
```

The bridge will start on `http://localhost:8000`

### 5. Connect Dojo

In another terminal, start the Dojo and point it to your bridge:

```bash
cd ../apps/dojo
export ADK_MIDDLEWARE_URL=http://localhost:8000
pnpm dev
```

Visit `http://localhost:3000/adk-middleware` to use your Agent Engine deployment!

## Configuration

All configuration is done via environment variables (`.env` file):

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `GCP_PROJECT_ID` | Your Google Cloud project ID | ✅ | - |
| `GCP_LOCATION` | GCP region for your agent | ✅ | `us-central1` |
| `AGENT_ENGINE_RESOURCE_ID` | Your agent's resource ID | ✅ | - |
| `GOOGLE_API_KEY` | Google API key for authentication | One of these | - |
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to service account JSON | One of these | - |
| `PORT` | Server port | ❌ | `8000` |
| `HOST` | Server host | ❌ | `0.0.0.0` |
| `APP_NAME` | Application name | ❌ | `dojo_bridge` |
| `SESSION_TIMEOUT_SECONDS` | Session timeout | ❌ | `1200` |
| `EXECUTION_TIMEOUT_SECONDS` | Execution timeout | ❌ | `600` |
| `MAX_CONCURRENT_EXECUTIONS` | Max concurrent requests | ❌ | `10` |

## API Endpoints

Once running, the bridge exposes:

- `GET /` - Service information
- `GET /health` - Health check
- `POST /chat` - Main agent endpoint (SSE streaming)
- `GET /docs` - Interactive API documentation

## Authentication

### Option 1: API Key

```bash
export GOOGLE_API_KEY='your-api-key'
```

Get an API key from: https://makersuite.google.com/app/apikey

### Option 2: Service Account

```bash
export GOOGLE_APPLICATION_CREDENTIALS='/path/to/service-account.json'
```

Or use Application Default Credentials:
```bash
gcloud auth application-default login
```

## Development

### Project Structure

```
agui-dojo-adk-bridge/
├── src/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application
│   ├── config.py               # Configuration management
│   └── agent_engine_client.py  # Agent Engine connection
├── pyproject.toml              # Python dependencies
├── .env.example                # Example configuration
├── .env                        # Your configuration (not in git)
└── README.md                   # This file
```

### Adding Features

To add new endpoints for different agent types (e.g., tool-based UI, human-in-the-loop):

1. Create multiple agent instances in `main.py`
2. Add them with different paths using `add_adk_fastapi_endpoint()`

Example:
```python
add_adk_fastapi_endpoint(app, chat_agent, path="/chat")
add_adk_fastapi_endpoint(app, tool_agent, path="/tool-ui")
add_adk_fastapi_endpoint(app, hitl_agent, path="/hitl")
```

### Testing

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest
```

## Troubleshooting

### Connection Failed

If you see "Agent Engine connection failed":
1. Verify your `GCP_PROJECT_ID`, `GCP_LOCATION`, and `AGENT_ENGINE_RESOURCE_ID` are correct
2. Check your authentication is set up correctly
3. Update `src/agent_engine_client.py` with the correct ADK API

### SSE Not Streaming

Make sure your dojo is using the correct URL:
```bash
export ADK_MIDDLEWARE_URL=http://localhost:8000
```

### CORS Issues

If running dojo on a different domain, update the CORS settings in `src/main.py`:
```python
allow_origins=["http://your-dojo-domain.com"]
```

## Deployment

### Local Development
Already covered above!

### Cloud Run
```bash
# Build and deploy
gcloud run deploy agui-dojo-bridge \
  --source . \
  --set-env-vars GCP_PROJECT_ID=$PROJECT_ID,GCP_LOCATION=$LOCATION,AGENT_ENGINE_RESOURCE_ID=$AGENT_ID
```

### Docker
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install -e .
CMD ["uv", "run", "start"]
```

## Learn More

- [Google ADK Documentation](https://google.github.io/adk-docs/)
- [AG-UI Protocol](https://github.com/ag-ui-protocol/ag-ui)
- [ADK Middleware](../integrations/adk-middleware/python/README.md)

## License

MIT

