"""Main FastAPI application for the AG-UI Dojo to Agent Engine bridge."""

import logging
import sys
from pathlib import Path
from datetime import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from ag_ui_adk import ADKAgent, add_adk_fastapi_endpoint

from .config import get_settings
from .agent_engine_client import create_agent_engine_client

# Create logs directory
logs_dir = Path(__file__).parent.parent / "logs"
logs_dir.mkdir(exist_ok=True)

# Create timestamped log file
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
event_log_file = logs_dir / f"events_{timestamp}.log"

# Configure logging with both console and file handlers
log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Console handler (stdout)
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter(log_format))

# File handler for detailed event logs
file_handler = logging.FileHandler(event_log_file, encoding='utf-8')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter(log_format))

# Configure root logger
logging.basicConfig(
    level=logging.DEBUG,
    format=log_format,
    handlers=[console_handler, file_handler],
)

# Set specific loggers to DEBUG to see event translation
logging.getLogger("ag_ui_adk.event_translator").setLevel(logging.DEBUG)
logging.getLogger("ag_ui_adk.adk_agent").setLevel(logging.DEBUG)
logging.getLogger("google_adk.google.adk.models.google_llm").setLevel(logging.DEBUG)
logger = logging.getLogger(__name__)

logger.info(f"📝 Event logs will be saved to: {event_log_file}")

# Load settings
settings = get_settings()

# Create FastAPI app
app = FastAPI(
    title="AG-UI Dojo to Agent Engine Bridge",
    description="Bridge service to connect AG-UI Dojo to Google Agent Engine deployments",
    version="0.1.0",
    debug=settings.debug,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your dojo domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Initialize the bridge on startup."""
    logger.info("=" * 60)
    logger.info("Starting AG-UI Dojo to Agent Engine Bridge")
    logger.info("=" * 60)
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Project ID: {settings.gcp_project_id}")
    logger.info(f"Location: {settings.gcp_location}")
    logger.info(f"Agent ID: {settings.agent_engine_resource_id}")
    logger.info(f"Port: {settings.port}")
    logger.info("=" * 60)


@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "service": "AG-UI Dojo to Agent Engine Bridge",
        "version": "0.1.0",
        "status": "running",
        "endpoints": {
            "chat": "/chat",
            "health": "/health",
            "docs": "/docs",
        },
        "configuration": {
            "project_id": settings.gcp_project_id,
            "location": settings.gcp_location,
            "agent_id": settings.agent_engine_resource_id,
        },
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


# Initialize the Agent Engine connection and ADK middleware
try:
    logger.info("Connecting to Agent Engine deployment...")
    
    # Create the agent client
    agent_engine_agent = create_agent_engine_client(
        project_id=settings.gcp_project_id,
        location=settings.gcp_location,
        agent_id=settings.agent_engine_resource_id,
        credentials_path=settings.google_application_credentials,
    )
    
    # Wrap with ADK middleware
    bridge_agent = ADKAgent(
        adk_agent=agent_engine_agent,
        app_name=settings.app_name,
        session_timeout_seconds=settings.session_timeout_seconds,
        execution_timeout_seconds=settings.execution_timeout_seconds,
        max_concurrent_executions=settings.max_concurrent_executions,
        use_in_memory_services=True,  # Use in-memory for simplicity
    )
    
    # Add the endpoint
    add_adk_fastapi_endpoint(app, bridge_agent, path="/chat")
    
    logger.info("✅ Agent Engine connection established successfully!")
    logger.info("✅ ADK middleware endpoint added at /chat")
    
except Exception as init_error:
    error_message = str(init_error)
    logger.error(f"❌ Failed to initialize Agent Engine connection: {error_message}")
    logger.error("The /chat endpoint will not be available.")
    logger.error("Please check your configuration and Agent Engine deployment.")
    
    # Add a placeholder endpoint that returns an SSE error event
    from fastapi import Request
    from fastapi.responses import StreamingResponse
    from ag_ui.core import RunErrorEvent, EventType, RunAgentInput
    from ag_ui.encoder import EventEncoder
    
    @app.post("/chat")
    async def chat_error(input_data: RunAgentInput, request: Request):
        """Return an SSE error event when Agent Engine is not configured."""
        accept_header = request.headers.get("accept")
        encoder = EventEncoder(accept=accept_header)
        
        async def error_generator():
            # Create a proper AG-UI error event
            error_event = RunErrorEvent(
                type=EventType.RUN_ERROR,
                message=f"Agent Engine connection not configured: {error_message}",
                code="AGENT_ENGINE_NOT_CONFIGURED"
            )
            yield encoder.encode(error_event)
        
        return StreamingResponse(error_generator(), media_type=encoder.get_content_type())


def run_dev():
    """Run the development server."""
    logger.info("Starting development server...")
    uvicorn.run(
        "src.main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
        log_level="debug" if settings.debug else "info",
    )


def run_prod():
    """Run the production server."""
    logger.info("Starting production server...")
    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        log_level="info",
    )


if __name__ == "__main__":
    run_dev()

