import asyncio
import logging
from collections.abc import AsyncGenerator

from ollama import AsyncClient, ResponseError

from app.config import settings

logger = logging.getLogger(__name__)

_CHAT_NUM_PREDICT = 350
_CLASSIFY_NUM_PREDICT = 15
_MAX_RETRIES = 3
_RETRY_BASE_DELAY = 1.0

_client = AsyncClient(host=settings.ollama_base_url)


async def call_llama(
    messages: list[dict[str, str]],
    temperature: float = 0.7,
    model: str | None = None,
    num_predict: int = _CHAT_NUM_PREDICT,
) -> str:
    resolved_model = model or settings.ollama_model

    for attempt in range(_MAX_RETRIES):
        try:
            response = await _client.chat(
                model=resolved_model,
                messages=messages,
                options={"temperature": temperature, "num_predict": num_predict},
            )
            return response.message.content or ""

        except ResponseError as exc:
            # 4xx from Ollama — model not found, bad request, etc. Not worth retrying.
            logger.error(
                "llm_response_error",
                extra={
                    "event": "llm_response_error",
                    "model": resolved_model,
                    "http_status": exc.status_code,
                    "error": exc.error,
                    "fallback_triggered": True,
                },
            )
            return ""

        except Exception as exc:
            is_last = attempt == _MAX_RETRIES - 1
            if not is_last:
                delay = _RETRY_BASE_DELAY * (2**attempt)
                logger.warning(
                    "llm_retry",
                    extra={
                        "event": "llm_retry",
                        "model": resolved_model,
                        "attempt": attempt + 1,
                        "max_retries": _MAX_RETRIES,
                        "error": str(exc),
                        "retry_in_seconds": delay,
                    },
                )
                await asyncio.sleep(delay)
            else:
                logger.error(
                    "llm_failure",
                    extra={
                        "event": "llm_failure",
                        "model": resolved_model,
                        "attempts": _MAX_RETRIES,
                        "error": str(exc),
                        "fallback_triggered": True,
                    },
                    exc_info=True,
                )

    return ""


async def stream_llama(
    messages: list[dict[str, str]],
    temperature: float = 0.7,
    model: str | None = None,
    num_predict: int = _CHAT_NUM_PREDICT,
) -> AsyncGenerator[str, None]:
    resolved_model = model or settings.ollama_model
    try:
        async for chunk in await _client.chat(
            model=resolved_model,
            messages=messages,
            options={"temperature": temperature, "num_predict": num_predict},
            stream=True,
        ):
            content = chunk.message.content
            if content:
                yield content
    except ResponseError as exc:
        logger.error(
            "llm_stream_response_error",
            extra={
                "event": "llm_stream_response_error",
                "model": resolved_model,
                "http_status": exc.status_code,
                "error": exc.error,
                "fallback_triggered": True,
            },
        )
    except Exception as exc:
        logger.error(
            "llm_stream_failure",
            extra={
                "event": "llm_stream_failure",
                "model": resolved_model,
                "error": str(exc),
                "fallback_triggered": True,
            },
            exc_info=True,
        )
