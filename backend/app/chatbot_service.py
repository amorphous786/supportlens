from app.llm_client import call_llama

_SYSTEM_PROMPT = (
    "You are a professional customer support agent for a SaaS billing platform. "
    "Keep responses concise, clear, and helpful."
)


async def generate_bot_response(user_message: str) -> str:
    """Send a single user message to llama3 and return the assistant reply.

    Each call is fully stateless — no conversation history is carried over.
    Returns an empty string if the LLM is unreachable or returns nothing.
    """
    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ]
    return await call_llama(messages)
