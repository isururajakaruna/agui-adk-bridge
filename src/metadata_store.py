"""
Metadata Store for CUSTOM events (thinking, session_stats)
Stores metadata separately so frontends can retrieve it without CopilotKit filtering.
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class MetadataStore:
    """In-memory store for conversation metadata."""
    
    def __init__(self, ttl_minutes: int = 60):
        self._store: Dict[str, Dict[str, Any]] = {}
        self._ttl_minutes = ttl_minutes
        
    def init_thread(self, thread_id: str):
        """Initialize storage for a new thread."""
        if thread_id not in self._store:
            self._store[thread_id] = {
                "thinking": [],
                "session_stats": None,
                "created_at": datetime.now(),
                "last_updated": datetime.now()
            }
            logger.debug(f"[MetadataStore] Initialized thread: {thread_id}")
    
    def add_thinking(self, thread_id: str, thinking_event: Dict[str, Any]):
        """Add a thinking event."""
        self.init_thread(thread_id)
        self._store[thread_id]["thinking"].append({
            **thinking_event,
            "timestamp": datetime.now().isoformat()
        })
        self._store[thread_id]["last_updated"] = datetime.now()
        logger.debug(f"[MetadataStore] Added thinking event to thread {thread_id}")
    
    def set_session_stats(self, thread_id: str, stats: Dict[str, Any]):
        """Set session statistics."""
        self.init_thread(thread_id)
        self._store[thread_id]["session_stats"] = stats
        self._store[thread_id]["last_updated"] = datetime.now()
        logger.debug(f"[MetadataStore] Set session stats for thread {thread_id}")
    
    def get_metadata(self, thread_id: str) -> Dict[str, Any]:
        """Get all metadata for a thread."""
        if thread_id not in self._store:
            return {
                "thinking": [],
                "session_stats": None,
                "lastUpdated": None
            }
        
        data = self._store[thread_id]
        return {
            "thinking": data["thinking"],
            "session_stats": data["session_stats"],
            "lastUpdated": data["last_updated"].isoformat() if data["last_updated"] else None
        }
    
    def cleanup_old_threads(self):
        """Remove threads older than TTL."""
        cutoff = datetime.now() - timedelta(minutes=self._ttl_minutes)
        to_remove = [
            tid for tid, data in self._store.items()
            if data["last_updated"] < cutoff
        ]
        for tid in to_remove:
            del self._store[tid]
            logger.info(f"[MetadataStore] Cleaned up old thread: {tid}")

# Global metadata store instance
metadata_store = MetadataStore(ttl_minutes=60)

