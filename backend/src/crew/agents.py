from typing import Any, List

from core.config import settings
from crew.custom_llm import QwenLLM

# Initialize Custom LLM (Global Fallback)
llm = QwenLLM(
    model=settings.OPENAI_MODEL_NAME,
    base_url=settings.OPENAI_API_BASE,
    api_key=settings.OPENAI_API_KEY,
    temperature=0.0,  # Deterministic for compliance
    max_tokens=2048,
)


def get_llm(callbacks: List[Any] | None = None) -> QwenLLM:
    """Factory to get LLM instance with callbacks."""
    return QwenLLM(
        model=settings.OPENAI_MODEL_NAME,
        base_url=settings.OPENAI_API_BASE,
        api_key=settings.OPENAI_API_KEY,
        temperature=0.0,
        max_tokens=2048,
        callbacks=callbacks,
    )


# CrewAgents class removed. Use AgentRegistry for dynamic agents.
