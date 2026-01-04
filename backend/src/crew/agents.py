from src.core.config import settings
from src.crew.custom_llm import QwenLLM

# Initialize Custom LLM
llm = QwenLLM(
    model=settings.OPENAI_MODEL_NAME,
    base_url=settings.OPENAI_API_BASE,
    api_key=settings.OPENAI_API_KEY,
    temperature=0.7,
    max_tokens=2048,
)


# CrewAgents class removed. Use AgentRegistry for dynamic agents.
