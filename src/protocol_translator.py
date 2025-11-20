"""
AG-UI Protocol Translator
Translates Google Agent Engine events to AG-UI Protocol events.
"""
import json
import logging
import uuid
import time
from typing import AsyncIterator, Dict, Any, Optional

logger = logging.getLogger(__name__)

class AGUIProtocolTranslator:
    """Translates Agent Engine events to AG-UI Protocol SSE events."""
    
    def __init__(self, metadata_store=None):
        self.thread_id: Optional[str] = None
        self.run_id: Optional[str] = None
        self.current_message_id: Optional[str] = None
        self.metadata_store = metadata_store  # Optional metadata storage
        
        # Track session statistics
        self.total_thinking_tokens = 0
        self.total_tool_calls = 0
        self.session_start_time: Optional[float] = None
        
        # Track text message streaming state
        self.message_started = False
        self.current_text_message_id: Optional[str] = None
        
    async def translate_stream(
        self,
        agent_engine_events: AsyncIterator[Dict[str, Any]],
        thread_id: str,
        run_id: str
    ) -> AsyncIterator[str]:
        """
        Translate Agent Engine events to AG-UI Protocol SSE events.
        
        Args:
            agent_engine_events: Async iterator of raw Agent Engine JSON events
            thread_id: Thread ID for this conversation
            run_id: Run ID for this execution
            
        Yields:
            SSE-formatted AG-UI Protocol events (as strings)
        """
        self.thread_id = thread_id
        self.run_id = run_id
        self.session_start_time = time.time()
        
        try:
            # Emit RUN_STARTED
            yield self._format_sse({
                "type": "RUN_STARTED",
                "threadId": thread_id,
                "runId": run_id
            })
            
            async for event in agent_engine_events:
                logger.debug(f"Translating Agent Engine event: {event.get('id', 'unknown')}")
                
                # Translate each event to AG-UI Protocol
                async for agui_event in self._translate_event(event):
                    yield agui_event
            
            # Calculate session duration
            duration_seconds = time.time() - self.session_start_time if self.session_start_time else 0
            
            # Send session statistics as ACTIVITY_SNAPSHOT (AG-UI Protocol native)
            session_stats_content = {
                "totalThinkingTokens": self.total_thinking_tokens,
                "totalToolCalls": self.total_tool_calls,
                "durationSeconds": round(duration_seconds, 2),
                "threadId": thread_id,
                "runId": run_id
            }
            
            session_stats_message_id = f"session-stats-{thread_id}-{run_id}"
            
            yield self._format_sse({
                "type": "ACTIVITY_SNAPSHOT",
                "messageId": session_stats_message_id,
                "activityType": "SESSION_STATS",
                "content": session_stats_content,
                "replace": True
            })
            
            logger.debug(f"📤 Sent ACTIVITY_SNAPSHOT for session stats (messageId: {session_stats_message_id})")
            
            # Store in metadata store if available
            if self.metadata_store and self.thread_id:
                self.metadata_store.set_session_stats(self.thread_id, session_stats_content)
            
            logger.info(f"📊 Session stats - Thinking tokens: {self.total_thinking_tokens}, Tool calls: {self.total_tool_calls}, Duration: {duration_seconds:.2f}s")
            
            # Close any open text message before finishing the stream
            if self.message_started and self.current_text_message_id:
                yield self._format_sse({
                    "type": "TEXT_MESSAGE_END",
                    "messageId": self.current_text_message_id
                })
                logger.debug(f"📤 TEXT_MESSAGE_END (stream complete)")
                self.message_started = False
                self.current_text_message_id = None
                    
            # Emit RUN_FINISHED
            yield self._format_sse({
                "type": "RUN_FINISHED",
                "threadId": thread_id,
                "runId": run_id
            })
            
        except Exception as e:
            logger.error(f"Error in translation stream: {e}", exc_info=True)
            # Emit RUN_ERROR
            yield self._format_sse({
                "type": "RUN_ERROR",
                "message": str(e),
                "code": "TRANSLATION_ERROR"
            })
    
    async def _translate_event(self, event: Dict[str, Any]) -> AsyncIterator[str]:
        """Translate a single Agent Engine event to AG-UI Protocol events."""
        
        content = event.get("content", {})
        parts = content.get("parts", [])
        
        if not parts:
            logger.debug("No parts in event, skipping")
            return
        
        # Process each part
        for part in parts:
            # Handle text messages
            if "text" in part:
                async for agui_event in self._handle_text_message(part, event):
                    yield agui_event
            
            # Handle function calls (tool calls)
            elif "function_call" in part:
                async for agui_event in self._handle_function_call(part):
                    yield agui_event
            
            # Handle function responses (tool results)
            elif "function_response" in part:
                async for agui_event in self._handle_function_response(part):
                    yield agui_event
    
    async def _handle_text_message(
        self, 
        part: Dict[str, Any],
        event: Dict[str, Any]
    ) -> AsyncIterator[str]:
        """Handle text message parts."""
        
        text = part.get("text", "")
        has_thinking = "thought_signature" in part
        
        if not text:
            return
        
        # Close any open text message before handling thinking (tool call)
        if has_thinking and self.message_started:
            yield self._format_sse({
                "type": "TEXT_MESSAGE_END",
                "messageId": self.current_text_message_id
            })
            logger.debug(f"📤 TEXT_MESSAGE_END (before thinking)")
            self.message_started = False
            self.current_text_message_id = None
        
        # If thinking is present, send as TOOL_CALL (so frontend can render without causing loop)
        if has_thinking:
            usage = event.get('usage_metadata', {})
            thoughts_token_count = usage.get('thoughts_token_count', 0)
            
            # Track total thinking tokens
            self.total_thinking_tokens += thoughts_token_count
            
            logger.info(f"🧠 Thinking detected (thoughts_token_count: {thoughts_token_count})")
            
            # Create unique tool call ID for this thinking event
            thinking_tool_id = f"thinking-{self.thread_id}-{int(time.time() * 1000)}"
            
            # Thinking data as tool arguments
            thinking_args = {
                "status": "in_progress",
                "thoughtsTokenCount": thoughts_token_count,
                "totalTokenCount": usage.get('total_token_count', 0),
                "candidatesTokenCount": usage.get('candidates_token_count', 0),
                "promptTokenCount": usage.get('prompt_token_count', 0),
                "model": event.get('model_version', 'unknown')
            }
            
            # Emit TOOL_CALL_START
            yield self._format_sse({
                "type": "TOOL_CALL_START",
                "toolCallId": thinking_tool_id,
                "toolCallName": "thinking_step"
            })
            
            # Emit TOOL_CALL_ARGS
            yield self._format_sse({
                "type": "TOOL_CALL_ARGS",
                "toolCallId": thinking_tool_id,
                "delta": json.dumps(thinking_args)
            })
            
            # Emit TOOL_CALL_END
            yield self._format_sse({
                "type": "TOOL_CALL_END",
                "toolCallId": thinking_tool_id
            })
            
            # Emit TOOL_CALL_RESULT (marks it as complete, prevents agent loop)
            yield self._format_sse({
                "type": "TOOL_CALL_RESULT",
                "messageId": f"result-{thinking_tool_id}",
                "toolCallId": thinking_tool_id,
                "content": json.dumps({"status": "complete"}),
                "role": "tool"
            })
            
            logger.debug(f"📤 Sent thinking as TOOL_CALL (toolCallId: {thinking_tool_id})")
            
            # Store in metadata store if available
            if self.metadata_store and self.thread_id:
                self.metadata_store.add_thinking(self.thread_id, thinking_args)
        
        # Start a new text message if not already started
        if not self.message_started:
            self.current_text_message_id = str(uuid.uuid4())
            self.message_started = True
            
            # Emit TEXT_MESSAGE_START (only once per message)
            yield self._format_sse({
                "type": "TEXT_MESSAGE_START",
                "messageId": self.current_text_message_id,
                "role": "assistant"
            })
            logger.debug(f"📤 TEXT_MESSAGE_START (messageId: {self.current_text_message_id})")
        
        # Emit TEXT_MESSAGE_CONTENT for this chunk (streaming delta)
        yield self._format_sse({
            "type": "TEXT_MESSAGE_CONTENT",
            "messageId": self.current_text_message_id,
            "delta": text
        })
        logger.debug(f"📤 TEXT_MESSAGE_CONTENT chunk ({len(text)} chars)")
        
        # Don't send TEXT_MESSAGE_END here - keep message open for streaming!
        
        # Send thinking completion as a separate tool call (optional - can be removed if not needed)
        # The initial thinking tool call already has a TOOL_CALL_RESULT marking it complete
        # This is just for tracking in metadata if needed
    
    async def _handle_function_call(self, part: Dict[str, Any]) -> AsyncIterator[str]:
        """Handle function call (tool call) parts."""
        
        # Close any open text message before starting a tool call
        if self.message_started:
            yield self._format_sse({
                "type": "TEXT_MESSAGE_END",
                "messageId": self.current_text_message_id
            })
            logger.debug(f"📤 TEXT_MESSAGE_END (before tool call)")
            self.message_started = False
            self.current_text_message_id = None
        
        function_call = part.get("function_call", {})
        tool_call_id = function_call.get("id", str(uuid.uuid4()))
        tool_name = function_call.get("name", "unknown")
        tool_args = function_call.get("args", {})
        
        # Track tool call count
        self.total_tool_calls += 1
        
        logger.info(f"🔧 Tool Call: {tool_name} (ID: {tool_call_id})")
        
        # Emit TOOL_CALL_START
        yield self._format_sse({
            "type": "TOOL_CALL_START",
            "toolCallId": tool_call_id,
            "toolCallName": tool_name
        })
        
        # Emit TOOL_CALL_ARGS (stream the full args as JSON)
        args_json = json.dumps(tool_args)
        yield self._format_sse({
            "type": "TOOL_CALL_ARGS",
            "toolCallId": tool_call_id,
            "delta": args_json
        })
        
        # Emit TOOL_CALL_END
        yield self._format_sse({
            "type": "TOOL_CALL_END",
            "toolCallId": tool_call_id
        })
    
    async def _handle_function_response(self, part: Dict[str, Any]) -> AsyncIterator[str]:
        """Handle function response (tool result) parts."""
        
        function_response = part.get("function_response", {})
        tool_call_id = function_response.get("id", str(uuid.uuid4()))
        tool_name = function_response.get("name", "unknown")
        response = function_response.get("response", {})
        
        logger.info(f"✅ Tool Result: {tool_name} (ID: {tool_call_id})")
        
        # Generate message ID for the tool result
        message_id = str(uuid.uuid4())
        
        # Emit TOOL_CALL_RESULT
        yield self._format_sse({
            "type": "TOOL_CALL_RESULT",
            "messageId": message_id,
            "toolCallId": tool_call_id,
            "content": json.dumps(response),
            "role": "tool"
        })
    
    def _format_sse(self, event: Dict[str, Any]) -> str:
        """Format an event as SSE (Server-Sent Events)."""
        return f"data: {json.dumps(event)}\n\n"

