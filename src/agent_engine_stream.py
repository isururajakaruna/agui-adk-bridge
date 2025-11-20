"""
Direct streaming client for Google Agent Engine.
Returns raw JSON events without ADK translation.
"""
import logging
import subprocess
import json
import httpx
from typing import Optional, AsyncIterator, Dict, Any
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

# Dedicated logger for raw Agent Engine communication
agent_engine_logger = logging.getLogger("agent_engine_raw")

# Configure the raw Agent Engine logger to write to a separate file
logs_dir = Path(__file__).parent.parent / "logs"
logs_dir.mkdir(exist_ok=True)
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
agent_engine_raw_log_file = logs_dir / f"agent_engine_raw_{timestamp}.log"

# Ensure the raw logger is configured only once
if not agent_engine_logger.handlers:
    raw_file_handler = logging.FileHandler(agent_engine_raw_log_file, encoding='utf-8')
    raw_file_handler.setLevel(logging.DEBUG)
    raw_file_handler.setFormatter(logging.Formatter("%(asctime)s - %(message)s"))
    agent_engine_logger.addHandler(raw_file_handler)
    agent_engine_logger.propagate = False  # Prevent events from being passed to root logger
    agent_engine_logger.setLevel(logging.DEBUG)
    logger.info(f"📝 Raw Agent Engine logs will be saved to: {agent_engine_raw_log_file}")


class AgentEngineStreamClient:
    """Streams raw events from Google Agent Engine (Vertex AI Reasoning Engine)."""
    
    def __init__(
        self,
        project_id: str,
        location: str,
        agent_id: str,
    ):
        """
        Initialize the Agent Engine streaming client.
        
        Args:
            project_id: Google Cloud project ID
            location: GCP location (e.g., 'us-central1')
            agent_id: Agent Engine resource ID
        """
        self.project_id = project_id
        self.location = location
        self.agent_id = agent_id
        
        # Build the endpoint URL
        agent_resource_name = (
            f"projects/{project_id}/locations/{location}/"
            f"reasoningEngines/{agent_id}"
        )
        self.endpoint_url = (
            f"https://{location}-aiplatform.googleapis.com/v1/{agent_resource_name}:streamQuery?alt=sse"
        )
        
        logger.info(
            f"Initialized Agent Engine client for Reasoning Engine {agent_id} "
            f"in project {project_id} at {location}"
        )
        logger.info(f"Endpoint: {self.endpoint_url}")
    
    def _get_auth_token(self) -> str:
        """Get Google Cloud access token using gcloud."""
        try:
            result = subprocess.run(
                ["gcloud", "auth", "print-access-token"],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to get access token: {e}")
            raise RuntimeError(
                "Failed to get access token. Please run: gcloud auth application-default login"
            )
    
    async def stream_query(
        self,
        message: str,
        user_id: Optional[str] = None,
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Stream events from the Agent Engine for a query.
        
        Args:
            message: User message to send to the agent
            user_id: Optional user ID for the session
            
        Yields:
            Raw Agent Engine JSON events
        """
        # Get auth token
        token = self._get_auth_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        
        # Build payload
        payload = {
            "class_method": "async_stream_query",
            "input": {
                "message": message,
                "user_id": user_id or "default-user"
            }
        }
        
        # Log the request
        agent_engine_logger.info("=" * 80)
        agent_engine_logger.info("REQUEST TO AGENT ENGINE:")
        agent_engine_logger.info(f"User Message: {message}")
        agent_engine_logger.info(f"Payload: {json.dumps(payload, indent=2)}")
        agent_engine_logger.info("=" * 80)
        
        logger.info(f"📤 Sending query to Agent Engine: '{message[:100]}...'")
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                async with client.stream(
                    "POST",
                    self.endpoint_url,
                    json=payload,
                    headers=headers,
                ) as response:
                    # Check for errors
                    if response.status_code != 200:
                        error_text = await response.aread()
                        error_msg = f"HTTP {response.status_code}: {error_text.decode()}"
                        agent_engine_logger.error(f"HTTP Error: {error_msg}")
                        logger.error(error_msg)
                        raise httpx.HTTPStatusError(
                            message=error_msg,
                            request=response.request,
                            response=response
                        )
                    
                    # Stream response lines
                    async for line in response.aiter_lines():
                        line = line.strip()
                        if not line:
                            continue
                        
                        try:
                            # Parse JSON
                            data = json.loads(line)
                            
                            # Log the raw response
                            agent_engine_logger.info("RAW AGENT ENGINE RESPONSE:")
                            agent_engine_logger.info(json.dumps(data, indent=2))
                            agent_engine_logger.info("-" * 40)
                            
                            # Yield the raw JSON event
                            yield data
                            
                        except json.JSONDecodeError as e:
                            agent_engine_logger.warning(f"Failed to parse JSON line: {e}")
                            logger.warning(f"Failed to parse JSON line from Agent Engine: {e}")
                            continue
                        except Exception as e:
                            agent_engine_logger.error(f"Error processing event: {e}", exc_info=True)
                            logger.error(f"Error processing Agent Engine event: {e}", exc_info=True)
                            continue
                    
                    agent_engine_logger.info("=" * 80)
                    agent_engine_logger.info("✅ STREAM COMPLETED FROM AGENT ENGINE")
                    agent_engine_logger.info("=" * 80)
                    logger.info("✅ Stream completed from Agent Engine")
                    
        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP {e.response.status_code} error: {e.response.text}"
            agent_engine_logger.error(f"HTTP Error calling Agent Engine: {error_msg}")
            logger.error(error_msg)
            raise
        except Exception as e:
            agent_engine_logger.error(f"Error calling Agent Engine: {e}", exc_info=True)
            logger.error(f"Error calling Agent Engine: {e}", exc_info=True)
            raise
