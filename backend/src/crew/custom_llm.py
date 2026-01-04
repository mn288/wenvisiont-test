from typing import Any, Dict, List

from crewai.llms.base_llm import BaseLLM
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI


class QwenLLM(BaseLLM):
    def __init__(self, model: str, base_url: str, api_key: str, **kwargs):
        self.model_name = model
        self.client = ChatOpenAI(model=model, base_url=base_url, api_key=api_key, streaming=True, **kwargs)
        super().__init__(model=model)

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

        # Helper noop for missing callback methods
        if callbacks:

            def noop(*args, **kwargs):
                pass

            for cb in callbacks:
                if not hasattr(cb, "raise_error"):
                    cb.raise_error = True

                # Missing attributes
                for attr in [
                    "ignore_chat_model",
                    "ignore_llm",
                    "ignore_agent",
                    "ignore_chain",
                    "ignore_retry",
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
        # CrewAI passes 'tools' in kwargs when calling the LLM
        if "tools" in kwargs:
            tools = kwargs.pop("tools")
            # Bind tools to the client (ChatOpenAI supports bind_tools)
            # We need to make sure we use a client that supports it.
            # ChatOpenAI does.
            client = self.client.bind_tools(tools)
        else:
            client = self.client

        # Ensure stop tokens are present to prevent hallucinating observations
        if "stop" not in kwargs:
            kwargs["stop"] = ["Observation:"]

        # Filter out internal CrewAI arguments that OpenAI doesn't support
        for invalid_arg in ["from_task", "from_agent", "response_model"]:
            if invalid_arg in kwargs:
                kwargs.pop(invalid_arg)

        response_content = ""
        # We perform manual iteration over the stream to ensure token events are emitted.
        # We DO NOT pass 'callbacks' in the config here, because passing explicit callbacks
        # overrides the LangChain context callbacks (which are needed for astream_events to work).
        # By omitting 'config={"callbacks": callbacks}', we allow the context callbacks to
        # attach to this run, enabling the SSE stream to capture tokens.
        for chunk in client.stream(lc_messages, **kwargs):
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

        # Helper noop for missing callback methods
        if callbacks:

            def noop(*args, **kwargs):
                pass

            for cb in callbacks:
                if not hasattr(cb, "raise_error"):
                    cb.raise_error = True

                # Missing attributes
                for attr in [
                    "ignore_chat_model",
                    "ignore_llm",
                    "ignore_agent",
                    "ignore_chain",
                    "ignore_retry",
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

        # Ensure stop tokens
        if "stop" not in kwargs:
            kwargs["stop"] = ["Observation:"]

        # Filter out internal CrewAI arguments
        for invalid_arg in ["from_task", "from_agent", "response_model"]:
            if invalid_arg in kwargs:
                kwargs.pop(invalid_arg)

        response_content = ""
        # Async stream iteration
        async for chunk in client.astream(lc_messages, **kwargs):
            response_content += chunk.content

        return response_content

    def supports_function_calling(self) -> bool:
        return True  # Qwen usually supports it, or we assume so for Agent usage

    def supports_stop_words(self) -> bool:
        return True
