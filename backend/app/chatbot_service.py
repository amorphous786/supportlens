from collections.abc import AsyncGenerator

from app.llm_client import call_llama, stream_llama

_SYSTEM_PROMPT = (
    "You are a professional customer support agent for a SaaS billing platform. "
    "Keep responses concise, clear, and helpful."
)


def _build_messages(user_message: str) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ]


async def generate_bot_response(user_message: str) -> str:
    """Send a single user message to llama3 and return the assistant reply.

    Each call is fully stateless — no conversation history is carried over.
    Returns an empty string if the LLM is unreachable or returns nothing.
    """
    return await call_llama(_build_messages(user_message))


async def stream_bot_response(user_message: str) -> AsyncGenerator[str, None]:
    """Stream the bot reply token by token.

    Yields text fragments as they arrive from Ollama so the caller can forward
    them to the client without waiting for the full response.
    """
    async for token in stream_llama(_build_messages(user_message)):
        yield token
