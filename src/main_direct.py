"""
AG-UI Dojo to Agent Engine Bridge - Direct Protocol Implementation
Bypasses ag_ui_adk middleware to directly translate Agent Engine events to AG-UI Protocol.
"""
import os
import logging
import uuid
from datetime import datetime
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Any, Optional

from .agent_engine_stream import AgentEngineStreamClient
from .protocol_translator import AGUIProtocolTranslator
from .config import get_settings
from .metadata_store import metadata_store

# Setup logging
logs_dir = Path(__file__).parent.parent / "logs"
logs_dir.mkdir(exist_ok=True)
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = logs_dir / f"events_{timestamp}.log"

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)
logger.info(f"📝 Event logs will be saved to: {log_file}")

# Load settings
settings = get_settings()

# Global client
agent_client: AgentEngineStreamClient = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan events for the FastAPI app."""
    global agent_client
    
    logger.info("=" * 60)
    logger.info("Starting AG-UI Dojo to Agent Engine Bridge")
    logger.info("Direct Protocol Implementation (No Middleware)")
    logger.info("=" * 60)
    
    # Initialize Agent Engine client
    try:
        logger.info("Connecting to Agent Engine deployment...")
        agent_client = AgentEngineStreamClient(
            project_id=settings.gcp_project_id,
            location=settings.gcp_location,
            agent_id=settings.agent_engine_resource_id,
        )
        logger.info("✅ Agent Engine client created successfully!")
    except Exception as e:
        logger.error(f"❌ Failed to initialize Agent Engine client: {e}")
        raise
    
    logger.info("=" * 60)
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Project ID: {settings.gcp_project_id}")
    logger.info(f"Location: {settings.gcp_location}")
    logger.info(f"Agent ID: {settings.agent_engine_resource_id}")
    logger.info(f"Port: {settings.port}")
    logger.info("=" * 60)
    
    yield
    
    logger.info("Shutting down bridge...")


# Create FastAPI app with direct protocol implementation
app = FastAPI(
    title=settings.app_name,
    description="AG-UI Protocol bridge to Google Agent Engine (Direct Implementation)",
    version="2.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response models (AG-UI Protocol format)
class Message(BaseModel):
    """AG-UI Protocol message."""
    id: str
    role: str
    content: Optional[Any] = None
    name: Optional[str] = None
    tool_call_id: Optional[str] = None
    tool_calls: Optional[List[Any]] = None

    class Config:
        extra = "allow"


class RunAgentInput(BaseModel):
    """AG-UI Protocol input format."""
    thread_id: Optional[str] = None
    run_id: Optional[str] = None
    parent_run_id: Optional[str] = None
    state: Optional[Any] = None
    messages: List[Message]
    tools: Optional[List[Any]] = None
    context: Optional[List[Any]] = None
    forwarded_props: Optional[Any] = None

    class Config:
        extra = "allow"


@app.post("/chat")
async def chat(input_data: RunAgentInput):
    """
    Chat endpoint that streams AG-UI Protocol events.
    
    This endpoint:
    1. Receives AG-UI Protocol input
    2. Streams raw events from Agent Engine
    3. Translates them to AG-UI Protocol
    4. Returns as Server-Sent Events (SSE)
    """
    global agent_client
    
    if agent_client is None:
        logger.error("Agent client not initialized")
        return StreamingResponse(
            iter([f"data: {{\"type\":\"RUN_ERROR\",\"message\":\"Agent client not initialized\",\"code\":\"NOT_INITIALIZED\"}}\n\n"]),
            media_type="text/event-stream"
        )
    
    # Extract user message from messages
    user_message = ""
    for msg in input_data.messages:
        if msg.role == "user":
            if isinstance(msg.content, str):
                user_message = msg.content
            elif isinstance(msg.content, list):
                # Handle multimodal content
                for part in msg.content:
                    if isinstance(part, dict) and part.get("type") == "text":
                        user_message = part.get("text", "")
                        break
            break
    
    if not user_message:
        logger.error("No user message found in request")
        return StreamingResponse(
            iter([f"data: {{\"type\":\"RUN_ERROR\",\"message\":\"No user message found\",\"code\":\"INVALID_INPUT\"}}\n\n"]),
            media_type="text/event-stream"
        )
    
    # Generate IDs
    thread_id = input_data.thread_id or str(uuid.uuid4())
    run_id = input_data.run_id or str(uuid.uuid4())
    user_id = "default-user"  # Can be extracted from context if needed
    
    logger.info(f"📨 Received chat request")
    logger.info(f"   Thread ID: {thread_id}")
    logger.info(f"   Run ID: {run_id}")
    logger.info(f"   User ID: {user_id}")
    logger.info(f"   Message: {user_message[:100]}...")
    
    async def event_generator():
        """Generate AG-UI Protocol events from Agent Engine stream."""
        try:
            # Get Agent Engine stream
            agent_stream = agent_client.stream_query(
                message=user_message,
                user_id=user_id
            )
            
            # Create protocol translator with metadata storage
            translator = AGUIProtocolTranslator(metadata_store=metadata_store)
            
            # Translate and stream events
            async for agui_event in translator.translate_stream(
                agent_stream,
                thread_id=thread_id,
                run_id=run_id
            ):
                logger.debug(f"📤 Streaming AG-UI event: {agui_event[:100]}...")
                yield agui_event
                
        except Exception as e:
            logger.error(f"❌ Error in event stream: {e}", exc_info=True)
            error_event = f'data: {{"type":"RUN_ERROR","message":"{str(e)}","code":"STREAM_ERROR"}}\n\n'
            yield error_event
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.get("/metadata/{thread_id}")
async def get_metadata(thread_id: str):
    """
    Get metadata (thinking events, session stats) for a specific thread.
    This endpoint provides CUSTOM events that CopilotKit filters out.
    """
    logger.debug(f"Metadata requested for thread: {thread_id}")
    metadata = metadata_store.get_metadata(thread_id)
    logger.debug(f"Returning metadata: thinking events={len(metadata['thinking'])}, has_stats={metadata['session_stats'] is not None}")
    return metadata


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": "2.0.0",
        "implementation": "direct-protocol",
        "agent_connected": agent_client is not None
    }


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": settings.app_name,
        "description": "AG-UI Protocol bridge to Google Agent Engine (Direct Implementation)",
        "version": "2.0.0",
        "endpoints": {
            "/chat": "POST - Chat with the agent (AG-UI Protocol SSE)",
            "/metadata/{thread_id}": "GET - Get metadata (thinking, stats) for a thread",
            "/health": "GET - Health check",
            "/": "GET - This message"
        }
    }


if __name__ == "__main__":
    import uvicorn
    
    logger.info("Starting development server...")
    uvicorn.run(
        "src.main_direct:app",
        host="0.0.0.0",
        port=settings.port,
        reload=True,
        log_level="info"
    )

