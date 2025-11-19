"""Client for connecting to Google Agent Engine deployments."""

import logging
from typing import Optional, AsyncIterator
import subprocess
import json
import httpx
from google.adk.agents import BaseAgent
from google.adk.events import Event
from google.genai import types as genai_types

logger = logging.getLogger(__name__)


class ReasoningEngineAgent(BaseAgent):
    """
    Custom ADK Agent that wraps a Vertex AI Reasoning Engine deployment.
    
    This makes REST API calls to the Reasoning Engine endpoint and translates
    responses to ADK events.
    """
    
    def __init__(
        self,
        project_id: str,
        location: str,
        reasoning_engine_id: str,
    ):
        """
        Initialize the Reasoning Engine agent.
        
        Args:
            project_id: Google Cloud project ID
            location: GCP location (e.g., 'us-central1')
            reasoning_engine_id: Reasoning Engine resource ID
        """
        super().__init__(name=f"reasoning_engine_{reasoning_engine_id}")
        
        # Store configuration in a dict to avoid Pydantic field issues
        self._config = {
            'project_id': project_id,
            'location': location,
            'reasoning_engine_id': reasoning_engine_id,
        }
        
        # Build the endpoint URL - use streamQuery with SSE
        agent_resource_name = (
            f"projects/{project_id}/locations/{location}/"
            f"reasoningEngines/{reasoning_engine_id}"
        )
        self._endpoint_url = (
            f"https://{location}-aiplatform.googleapis.com/v1/{agent_resource_name}:streamQuery?alt=sse"
        )
        
        logger.info(
            f"Initialized Reasoning Engine agent: {reasoning_engine_id} "
            f"in project {project_id} at {location}"
        )
        logger.info(f"Endpoint: {self._endpoint_url}")
    
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
            logger.error(f"Failed to get access token. Make sure you're logged in with 'gcloud auth login'. Error: {e}")
            raise RuntimeError("Failed to get access token. Please run: gcloud auth login")
    
    async def _run_async_impl(
        self,
        instruction: Optional[str] = None,
        messages: Optional[list] = None,
        **kwargs
    ) -> AsyncIterator[Event]:
        """
        Internal implementation to run the Reasoning Engine and yield ADK events.
        
        This is the method that BaseAgent expects to be overridden.
        
        Args:
            instruction: System instruction (if supported)
            messages: List of messages to send
            **kwargs: Additional parameters
            
        Yields:
            Event: ADK events from the Reasoning Engine
        """
        # Debug logging
        logger.info(f"_run_async_impl called with:")
        logger.info(f"  instruction: {instruction}")
        logger.info(f"  messages type: {type(messages)}")
        logger.info(f"  messages length: {len(messages) if messages else 0}")
        logger.info(f"  kwargs keys: {list(kwargs.keys())}")
        logger.info(f"  kwargs: {kwargs}")
        if messages:
            for i, msg in enumerate(messages):
                logger.info(f"  message[{i}]: type={type(msg)}, value={msg}")
                if hasattr(msg, '__dict__'):
                    logger.info(f"  message[{i}] attributes: {msg.__dict__}")
        
        # Build the request payload
        # Extract the user message from the instruction (RunContext)
        # ADK Runner passes a RunContext object as 'instruction' with user_content
        user_message = ""
        
        if instruction and hasattr(instruction, 'user_content'):
            # Extract from user_content (Content object)
            user_content = instruction.user_content
            if hasattr(user_content, 'parts') and user_content.parts:
                user_message = " ".join([
                    part.text if hasattr(part, 'text') else str(part)
                    for part in user_content.parts
                ])
        elif messages and len(messages) > 0:
            # Fallback: try to extract from messages if provided
            last_msg = messages[-1]
            if hasattr(last_msg, 'parts') and last_msg.parts:
                user_message = " ".join([
                    part.text if hasattr(part, 'text') else str(part)
                    for part in last_msg.parts
                ])
            elif hasattr(last_msg, 'content'):
                if isinstance(last_msg.content, str):
                    user_message = last_msg.content
                elif hasattr(last_msg.content, 'parts'):
                    user_message = " ".join([
                        part.text if hasattr(part, 'text') else str(part)
                        for part in last_msg.content.parts
                    ])
        
        logger.info(f"Extracted user message: {user_message}")
        
        # Use the working format from the reference implementation
        # Generate a user_id (you can make this more sophisticated)
        import uuid
        user_id = str(uuid.uuid4())
        
        payload = {
            "class_method": "async_stream_query",
            "input": {
                "message": user_message,
                "user_id": user_id
            }
        }
        
        headers = {
            "Authorization": f"Bearer {self._get_auth_token()}",
            "Content-Type": "application/json",
        }
        
        logger.info(f"Calling Reasoning Engine with message: {user_message[:100]}...")
        logger.info(f"Payload: {payload}")
        
        try:
            # Use streaming endpoint
            async with httpx.AsyncClient(timeout=60.0) as client:
                async with client.stream(
                    "POST",
                    self._endpoint_url,
                    json=payload,
                    headers=headers,
                ) as response:
                    
                    if response.status_code != 200:
                        error_text = await response.aread()
                        error_msg = f"HTTP {response.status_code}: {error_text.decode('utf-8')}"
                        logger.error(error_msg)
                        
                        # Yield error event
                        from google.adk.events import Event
                        yield Event(
                            author="model",
                            content=genai_types.Content(
                                role="model",
                                parts=[genai_types.Part(text=f"Error: {error_msg}")]
                            )
                        )
                        return
                    
                    # Process streaming response line by line
                    # Accumulate text and yield as complete events
                    async for line in response.aiter_lines():
                        line = line.strip()
                        
                        if not line:
                            continue
                        
                        try:
                            # Parse JSON response (GCP returns JSON directly, not SSE format)
                            data = json.loads(line)
                            
                            # Log the FULL raw event first
                            logger.info(f"📦 RAW GCP EVENT:")
                            logger.info(json.dumps(data, indent=2))
                            
                            # Log event details for debugging
                            if isinstance(data, dict):
                                logger.info(f"📦 GCP Event - Keys: {list(data.keys())}")
                                if 'author' in data:
                                    logger.info(f"   Author: {data['author']}")
                                if 'content' in data:
                                    content_data = data['content']
                                    if isinstance(content_data, dict) and 'parts' in content_data:
                                        for i, part in enumerate(content_data['parts']):
                                            part_types = [k for k in part.keys() if k != 'text' or part.get('text')]
                                            if 'function_call' in part:
                                                logger.info(f"   🔧 Tool Call: {part['function_call'].get('name', 'unknown')}")
                                            elif 'function_response' in part:
                                                logger.info(f"   ✅ Tool Response: {part['function_response'].get('name', 'unknown')}")
                                            elif 'text' in part:
                                                text_preview = part['text'][:100] if len(part['text']) > 100 else part['text']
                                                logger.info(f"   💬 Text: {text_preview}")
                            
                            # Create ADK Event from the GCP response
                            # The GCP response already has the right structure with 'content' and 'parts'
                            if isinstance(data, dict) and 'content' in data:
                                content_data = data['content']
                                
                                # Convert to genai_types.Content
                                parts = []
                                if isinstance(content_data, dict) and 'parts' in content_data:
                                    for part_dict in content_data['parts']:
                                        # Check for thinking/reasoning content (thought_signature)
                                        if 'thought_signature' in part_dict:
                                            logger.info(f"   🧠 Thinking/reasoning detected (thought_signature present)")
                                            # Note: thought_signature is typically a base64-encoded or encrypted representation
                                            # The actual thinking text should be in the 'text' field of the same part
                                        
                                        if 'text' in part_dict:
                                            parts.append(genai_types.Part(text=part_dict['text']))
                                        elif 'function_call' in part_dict:
                                            # Handle function calls - these show as tool calls in dojo
                                            logger.info(f"   🔧 Creating Part with function_call: {part_dict['function_call']}")
                                            parts.append(genai_types.Part(function_call=part_dict['function_call']))
                                        elif 'function_response' in part_dict:
                                            # Handle function responses - these show as tool results in dojo
                                            logger.info(f"   ✅ Creating Part with function_response: {part_dict['function_response']}")
                                            parts.append(genai_types.Part(function_response=part_dict['function_response']))
                                
                                if parts:
                                    # Create ADK Event with author field
                                    from google.adk.events import Event
                                    author = data.get('author', 'model')
                                    
                                    # Create the event - ADK middleware will translate it to AG-UI protocol
                                    event = Event(
                                        author=author,
                                        content=genai_types.Content(
                                            role=content_data.get('role', 'model'),
                                            parts=parts
                                        )
                                    )
                                    
                                    # Check if the Event has the expected helper methods
                                    logger.info(f"   🔍 Event methods: {[m for m in dir(event) if 'function' in m.lower()]}")
                                    if hasattr(event, 'get_function_calls'):
                                        calls = event.get_function_calls()
                                        logger.info(f"   📞 get_function_calls() returned: {len(calls) if calls else 0} calls")
                                        if calls:
                                            logger.info(f"   📞 Function calls details: {[{'id': fc.id, 'name': fc.name} for fc in calls]}")
                                    if hasattr(event, 'get_function_responses'):
                                        responses = event.get_function_responses()
                                        logger.info(f"   📞 get_function_responses() returned: {len(responses) if responses else 0} responses")
                                        if responses:
                                            logger.info(f"   📞 Function responses details: {[{'id': fr.id, 'name': fr.name} for fr in responses]}")
                                    
                                    logger.debug(f"   ✅ Yielding ADK Event with {len(parts)} parts")
                                    yield event
                        
                        except json.JSONDecodeError as e:
                            logger.warning(f"Failed to parse JSON line: {e}")
                            continue
                        except Exception as e:
                            logger.error(f"Error processing event: {e}", exc_info=True)
                            continue
                    
                    logger.info(f"✅ Stream completed from Reasoning Engine")
                
        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP {e.response.status_code} error: {e.response.text}"
            logger.error(error_msg)
            # Yield an error response
            from google.adk.events import Event
            yield Event(
                author="model",
                content=genai_types.Content(
                    role="model",
                    parts=[genai_types.Part(text=f"Error calling Reasoning Engine: {error_msg}")]
                )
            )
        except Exception as e:
            logger.error(f"Error calling Reasoning Engine: {e}", exc_info=True)
            from google.adk.events import Event
            yield Event(
                author="model",
                content=genai_types.Content(
                    role="model",
                    parts=[genai_types.Part(text=f"Error: {str(e)}")]
                )
            )


class AgentEngineClient:
    """
    Client to connect to a deployed Google Agent Engine agent.
    
    This creates an ADK-compatible agent interface for agents deployed
    on Google's Agent Engine (Vertex AI Reasoning Engine).
    """
    
    def __init__(
        self,
        project_id: str,
        location: str,
        agent_id: str,
        credentials_path: Optional[str] = None,
    ):
        """
        Initialize the Agent Engine client.
        
        Args:
            project_id: Google Cloud project ID
            location: GCP location (e.g., 'us-central1')
            agent_id: Agent Engine/Reasoning Engine resource ID
            credentials_path: Optional path to service account JSON (not used for default credentials)
        """
        self.project_id = project_id
        self.location = location
        self.agent_id = agent_id
        
        logger.info(
            f"Initialized Agent Engine client for Reasoning Engine {agent_id} "
            f"in project {project_id} at {location}"
        )
    
    def get_agent(self) -> BaseAgent:
        """
        Get the ADK agent interface for the deployed Reasoning Engine.
        
        Returns:
            BaseAgent: An ADK Agent instance connected to the deployed Reasoning Engine
        """
        return ReasoningEngineAgent(
            project_id=self.project_id,
            location=self.location,
            reasoning_engine_id=self.agent_id,
        )


def create_agent_engine_client(
    project_id: str,
    location: str,
    agent_id: str,
    credentials_path: Optional[str] = None,
) -> BaseAgent:
    """
    Create and return an ADK agent connected to Reasoning Engine.
    
    Args:
        project_id: Google Cloud project ID
        location: GCP location
        agent_id: Reasoning Engine resource ID
        credentials_path: Optional service account path (uses default credentials if not provided)
        
    Returns:
        BaseAgent: ADK Agent instance connected to the deployed Reasoning Engine
    """
    client = AgentEngineClient(
        project_id=project_id,
        location=location,
        agent_id=agent_id,
        credentials_path=credentials_path,
    )
    return client.get_agent()

