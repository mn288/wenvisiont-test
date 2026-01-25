"""Token estimation and budgeting utilities.

Simple token approximation for context window management.
For production, consider using tiktoken for exact counts.
"""


def estimate_tokens(text: str) -> int:
    """Approximate token count (4 chars ≈ 1 token for English).

    This is a rough heuristic. For precise counts, use tiktoken.
    """
    if not text:
        return 0
    return len(text) // 4


def truncate_to_token_budget(text: str, max_tokens: int, suffix: str = "\n... [truncated]") -> str:
    """Truncate text to fit within token budget.

    Args:
        text: Input text to truncate
        max_tokens: Maximum token budget
        suffix: Text appended when truncation occurs

    Returns:
        Original text if within budget, otherwise truncated with suffix
    """
    if not text:
        return ""

    estimated = estimate_tokens(text)
    if estimated <= max_tokens:
        return text

    # Conservative: 3 chars per token to account for overhead
    max_chars = max_tokens * 3
    return text[:max_chars] + suffix
