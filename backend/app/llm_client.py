import logging

from ollama import AsyncClient, ResponseError

logger = logging.getLogger(__name__)

# host.docker.internal resolves to the host machine from inside a Docker container,
# allowing the backend container to reach Ollama running on the host (or in another container).
_OLLAMA_BASE_URL = "http://host.docker.internal:11434"
_DEFAULT_MODEL = "llama3"

_client = AsyncClient(host=_OLLAMA_BASE_URL)


async def call_llama(
    messages: list[dict[str, str]],
    temperature: float = 0.7,
    model: str = _DEFAULT_MODEL,
) -> str:
    """Send a chat-style message list to llama3 via Ollama and return the reply text.

    Args:
        messages:    OpenAI-style message dicts, e.g.
                     [{"role": "user", "content": "Hello"}]
        temperature: Sampling temperature (0 = deterministic, 1 = creative).
        model:       Ollama model tag to use.

    Returns:
        The generated text string, or an empty string on failure.

    Raises:
        Nothing — all exceptions are caught and logged so callers stay stable.
    """
    try:
        response = await _client.chat(
            model=model,
            messages=messages,
            options={"temperature": temperature},
        )
        return response.message.content or ""

    except ResponseError as exc:
        logger.error("Ollama ResponseError (status %s): %s", exc.status_code, exc.error)
        return ""

    except Exception as exc:  # network errors, model not found, etc.
        logger.error("Unexpected error calling Ollama: %s", exc, exc_info=True)
        return ""
