import logging
from collections.abc import AsyncGenerator

from ollama import AsyncClient, ResponseError

logger = logging.getLogger(__name__)

# host.docker.internal resolves to the host machine from inside a Docker container,
# allowing the backend container to reach Ollama running on the host (or in another container).
_OLLAMA_BASE_URL = "http://host.docker.internal:11434"
_DEFAULT_MODEL = "llama3"

# Maximum tokens for each use-case. Keeping these tight is the single biggest
# latency lever — Ollama stops generating as soon as num_predict is reached.
_CHAT_NUM_PREDICT = 350       # enough for a thorough support reply
_CLASSIFY_NUM_PREDICT = 15    # only one category label is ever needed

_client = AsyncClient(host=_OLLAMA_BASE_URL)


async def call_llama(
    messages: list[dict[str, str]],
    temperature: float = 0.7,
    model: str = _DEFAULT_MODEL,
    num_predict: int = _CHAT_NUM_PREDICT,
) -> str:
    """Send a chat-style message list to Ollama and return the reply text.

    Args:
        messages:    OpenAI-style message dicts, e.g.
                     [{"role": "user", "content": "Hello"}]
        temperature: Sampling temperature (0 = deterministic, 1 = creative).
        model:       Ollama model tag to use.
        num_predict: Maximum tokens to generate. Lower = faster response.

    Returns:
        The generated text string, or an empty string on failure.

    Raises:
        Nothing — all exceptions are caught and logged so callers stay stable.
    """
    try:
        response = await _client.chat(
            model=model,
            messages=messages,
            options={"temperature": temperature, "num_predict": num_predict},
        )
        return response.message.content or ""

    except ResponseError as exc:
        logger.error("Ollama ResponseError (status %s): %s", exc.status_code, exc.error)
        return ""

    except Exception as exc:  # network errors, model not found, etc.
        logger.error("Unexpected error calling Ollama: %s", exc, exc_info=True)
        return ""


async def stream_llama(
    messages: list[dict[str, str]],
    temperature: float = 0.7,
    model: str = _DEFAULT_MODEL,
    num_predict: int = _CHAT_NUM_PREDICT,
) -> AsyncGenerator[str, None]:
    """Stream tokens from Ollama one chunk at a time.

    Yields each text fragment as it arrives so callers can forward them to the
    client immediately rather than waiting for the full response.

    Args:
        messages:    OpenAI-style message dicts.
        temperature: Sampling temperature.
        model:       Ollama model tag to use.
        num_predict: Maximum tokens to generate.

    Yields:
        Non-empty text fragments from the model.
    """
    try:
        async for chunk in await _client.chat(
            model=model,
            messages=messages,
            options={"temperature": temperature, "num_predict": num_predict},
            stream=True,
        ):
            content = chunk.message.content
            if content:
                yield content

    except ResponseError as exc:
        logger.error("Ollama ResponseError (status %s): %s", exc.status_code, exc.error)

    except Exception as exc:
        logger.error("Unexpected error streaming Ollama: %s", exc, exc_info=True)
