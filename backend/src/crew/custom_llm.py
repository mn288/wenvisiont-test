import asyncio  # Lazy import or move to top
import logging
from typing import Any, Dict, List

from crewai.llms.base_llm import BaseLLM
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)


class QwenLLM(BaseLLM):
    def __init__(self, model: str, base_url: str, api_key: str, callbacks: List[Any] | None = None, **kwargs):
        self.model_name = model
        self.callbacks = callbacks or []
        self.client = ChatOpenAI(model=model, base_url=base_url, api_key=api_key, streaming=True, **kwargs)
        super().__init__(model=model)

    def _merge_callbacks(self, runtime_callbacks: List[Any] | None) -> List[Any]:
        merged = (self.callbacks or []) + (runtime_callbacks or [])
        return merged

    def call(
        self,
        messages: List[Dict[str, str]] | str,
        callbacks: List[Any] | None = None,
        **kwargs,
    ) -> str:
        if isinstance(messages, str):
            lc_messages = [HumanMessage(content=messages)]
        else:
            lc_messages = []
            for msg in messages:
                role = msg.get("role")
                content = msg.get("content")
                if role == "user":
                    lc_messages.append(HumanMessage(content=content))
                elif role == "assistant":
                    lc_messages.append(AIMessage(content=content))
                elif role == "system":
                    lc_messages.append(SystemMessage(content=content))
                else:
                    lc_messages.append(HumanMessage(content=content))

        # Merge callbacks
        active_callbacks = self._merge_callbacks(callbacks)

        # Helper noop for missing callback methods
        if active_callbacks:

            def noop(*args, **kwargs):
                pass

            for cb in active_callbacks:
                if not hasattr(cb, "raise_error"):
                    cb.raise_error = True

                # Missing attributes
                for attr in [
                    "ignore_chat_model",
                    "ignore_llm",
                    "ignore_agent",
                    "ignore_chain",
                    "ignore_retry",
                    "run_inline",
                ]:
                    if not hasattr(cb, attr):
                        setattr(cb, attr, False)

                # Missing methods
                methods = [
                    "on_chat_model_start",
                    "on_llm_start",
                    "on_llm_new_token",
                    "on_llm_end",
                    "on_llm_error",
                    "on_chain_start",
                    "on_chain_end",
                    "on_chain_error",
                    "on_tool_start",
                    "on_tool_end",
                    "on_tool_error",
                    "on_text",
                ]
                for method in methods:
                    if not hasattr(cb, method):
                        setattr(cb, method, noop)

        # Handle tools if passed
        if "tools" in kwargs:
            tools = kwargs.pop("tools")
            client = self.client.bind_tools(tools)
        else:
            client = self.client

        if "stop" not in kwargs:
            kwargs["stop"] = ["Observation:"]

        for invalid_arg in ["from_task", "from_agent", "response_model"]:
            if invalid_arg in kwargs:
                kwargs.pop(invalid_arg)

        response_content = ""
        # Pass callbacks in config to ensure LangFuse/others catch it.
        # This might duplicate events if context is already active, but for CrewAI (often isolated) it is safer.
        stream_config = {"callbacks": active_callbacks} if active_callbacks else None
        
        for chunk in client.stream(lc_messages, config=stream_config, **kwargs):
            response_content += chunk.content

        return response_content

    async def acall(
        self,
        messages: List[Dict[str, str]] | str,
        callbacks: List[Any] | None = None,
        **kwargs,
    ) -> str:
        if isinstance(messages, str):
            lc_messages = [HumanMessage(content=messages)]
        else:
            lc_messages = []
            for msg in messages:
                role = msg.get("role")
                content = msg.get("content")
                if role == "user":
                    lc_messages.append(HumanMessage(content=content))
                elif role == "assistant":
                    lc_messages.append(AIMessage(content=content))
                elif role == "system":
                    lc_messages.append(SystemMessage(content=content))
                else:
                    lc_messages.append(HumanMessage(content=content))

        # Merge callbacks
        active_callbacks = self._merge_callbacks(callbacks)
        
        # DEBUG: Observability Check
        if active_callbacks:
            callback_names = [cb.__class__.__name__ for cb in active_callbacks]
            logger.debug(f"QwenLLM.acall using callbacks: {callback_names}")

        # Helper noop for missing callback methods
        if active_callbacks:

            def noop(*args, **kwargs):
                pass

            for cb in active_callbacks:
                if not hasattr(cb, "raise_error"):
                    cb.raise_error = True

                # Missing attributes
                for attr in [
                    "ignore_chat_model",
                    "ignore_llm",
                    "ignore_agent",
                    "ignore_chain",
                    "ignore_retry",
                    "run_inline",
                ]:
                    if not hasattr(cb, attr):
                        setattr(cb, attr, False)

                # Missing methods
                methods = [
                    "on_chat_model_start",
                    "on_llm_start",
                    "on_llm_new_token",
                    "on_llm_end",
                    "on_llm_error",
                    "on_chain_start",
                    "on_chain_end",
                    "on_chain_error",
                    "on_tool_start",
                    "on_tool_end",
                    "on_tool_error",
                    "on_text",
                ]
                for method in methods:
                    if not hasattr(cb, method):
                        setattr(cb, method, noop)

        # Handle tools
        if "tools" in kwargs:
            tools = kwargs.pop("tools")
            client = self.client.bind_tools(tools)
        else:
            client = self.client

        if "stop" not in kwargs:
            kwargs["stop"] = ["Observation:"]

        for invalid_arg in ["from_task", "from_agent", "response_model"]:
            if invalid_arg in kwargs:
                kwargs.pop(invalid_arg)

        response_content = ""
        
        stream_config = {"callbacks": active_callbacks} if active_callbacks else None

        try:
            async for chunk in client.astream(lc_messages, config=stream_config, **kwargs):
                # Explicitly check for cancellation to ensure we stop generating
                if asyncio.current_task().cancelled():
                    logger.warning("QwenLLM: Task cancelled during generation loop.")
                    raise asyncio.CancelledError("Task cancelled during generation loop.")
                
                response_content += chunk.content
        except asyncio.CancelledError:
            logger.warning("QwenLLM: Generation cancelled.")
            raise

        return response_content

    def supports_function_calling(self) -> bool:
        return True

    def supports_stop_words(self) -> bool:
        return True

