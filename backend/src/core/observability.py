import hashlib
import logging
import os
from typing import Any, Dict, List, Optional
from uuid import UUID

# Langfuse v3 imports
from langfuse import Langfuse
from langfuse.langchain import CallbackHandler

# Enable Debug Logging for Langfuse
logging.getLogger("langfuse").setLevel(logging.DEBUG)
logger = logging.getLogger(__name__)

def _ensure_langfuse_env():
    """Ensure LANGFUSE_HOST is set for the SDK (handles LANGFUSE_BASE_URL alias)."""
    if not os.getenv("LANGFUSE_HOST"):
        base_url = os.getenv("LANGFUSE_BASE_URL")
        if base_url:
            os.environ["LANGFUSE_HOST"] = base_url
            logger.debug(f"Set LANGFUSE_HOST to {base_url}")

# Run once on module load
_ensure_langfuse_env()


class AntigravityCallbackHandler(CallbackHandler):
    """
    Custom CallbackHandler for Langfuse v3.
    
    The Langfuse CallbackHandler reads configuration from environment variables.
    This subclass injects session_id, user_id, and tags via metadata on each 
    callback event, which is the v3 recommended pattern.
    """
    def __init__(
        self,
        trace_id: str,
        user_id: Optional[str] = None,
        trace_name: Optional[str] = None,
        tags: Optional[List[str]] = None,
        **kwargs
    ):
        self._original_trace_id = trace_id
        self._user_id = user_id
        self._tags = tags or []
        self._trace_name = trace_name
        
        # Deterministic Session ID from trace_id
        try:
            self._session_id = UUID(trace_id).hex
        except ValueError:
            hash_hex = hashlib.md5(trace_id.encode()).hexdigest()
            self._session_id = UUID(hash_hex).hex
        
        # Initialize base CallbackHandler (no constructor args in v3!)
        super().__init__(**kwargs)
        
        logger.debug(f"AntigravityCallbackHandler initialized - session: {self._session_id}, user: {self._user_id}")

    def _inject_metadata(self, metadata: Optional[Dict[str, Any]], parent_run_id: Optional[UUID]) -> Dict[str, Any]:
        """
        Inject Langfuse metadata (session_id, user_id, tags) if this is a root run.
        Per Langfuse v3 docs, these are passed via metadata with langfuse_ prefix.
        """
        if parent_run_id is not None:
            return metadata or {}

        metadata = metadata or {}
        
        # Langfuse v3 metadata keys
        metadata["langfuse_session_id"] = self._session_id
        
        if self._user_id:
            metadata["langfuse_user_id"] = self._user_id
        
        if self._tags:
            current_tags = metadata.get("langfuse_tags", [])
            metadata["langfuse_tags"] = list(set(current_tags + self._tags))

        # Debug metadata
        metadata["thread_id"] = self._session_id
        if self._original_trace_id != self._session_id:
            metadata["original_thread_id"] = self._original_trace_id
        
        if self._trace_name:
            metadata["trace_name"] = self._trace_name
            
        return metadata

    def on_chain_start(
        self,
        serialized: Optional[Dict[str, Any]],
        inputs: Dict[str, Any],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Any:
        metadata = self._inject_metadata(metadata, parent_run_id)
        return super().on_chain_start(
            serialized, inputs, run_id=run_id, parent_run_id=parent_run_id, 
            tags=tags, metadata=metadata, **kwargs
        )

    def on_chat_model_start(
        self,
        serialized: Optional[Dict[str, Any]],
        messages: List[List[Any]],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Any:
        metadata = self._inject_metadata(metadata, parent_run_id)
        return super().on_chat_model_start(
            serialized, messages, run_id=run_id, parent_run_id=parent_run_id, 
            tags=tags, metadata=metadata, **kwargs
        )

    def on_llm_start(
        self,
        serialized: Optional[Dict[str, Any]],
        prompts: List[str],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Any:
        metadata = self._inject_metadata(metadata, parent_run_id)
        return super().on_llm_start(
            serialized, prompts, run_id=run_id, parent_run_id=parent_run_id, 
            tags=tags, metadata=metadata, **kwargs
        )

    def on_tool_start(
        self,
        serialized: Optional[Dict[str, Any]],
        input_str: str,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Any:
        metadata = self._inject_metadata(metadata, parent_run_id)
        return super().on_tool_start(
            serialized, input_str, run_id=run_id, parent_run_id=parent_run_id, 
            tags=tags, metadata=metadata, **kwargs
        )


def get_observability_callback(
    trace_id: str,
    user_id: Optional[str] = None,
    trace_name: Optional[str] = None,
    tags: Optional[list[str]] = None,
) -> CallbackHandler:
    """
    Returns a Langfuse v3 compatible callback handler.
    
    Args:
        trace_id: Thread/session identifier for grouping traces
        user_id: Optional user identifier  
        trace_name: Optional name for the trace
        tags: Optional list of tags
    """
    return AntigravityCallbackHandler(
        trace_id=trace_id,
        user_id=user_id,
        trace_name=trace_name,
        tags=tags,
    )


# --- GLOBAL SHUTDOWN HANDLING ---

_langfuse_client: Optional[Langfuse] = None

def get_langfuse_client() -> Langfuse:
    """
    Singleton accessor for the Langfuse client instance.
    Reads configuration from environment variables.
    """
    global _langfuse_client
    if _langfuse_client is None:
        _langfuse_client = Langfuse()
        logger.info(f"Langfuse client initialized with host: {os.getenv('LANGFUSE_HOST')}")
    return _langfuse_client

def shutdown_langfuse():
    """
    Call this on application shutdown to ensure all buffered traces 
    are sent to the server.
    """
    global _langfuse_client
    if _langfuse_client:
        print("Flushing Langfuse traces...")
        _langfuse_client.flush()
        print("Langfuse flush complete.")