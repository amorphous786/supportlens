import logging

from app.llm_client import _CLASSIFY_NUM_PREDICT, call_llama
from app.models import Category

logger = logging.getLogger(__name__)

_VALID_CATEGORIES: set[str] = {c.value for c in Category}
_DEFAULT_CATEGORY = Category.general_inquiry.value

_CLASSIFICATION_PROMPT = """\
You are a support ticket classifier for a SaaS billing platform.

TASK
----
Read the conversation below and output EXACTLY ONE category from the list.

CATEGORIES
----------
Billing
Refund
Account Access
Cancellation
General Inquiry

RULES (apply in this exact priority order)
-------------------------------------------
1. If the user explicitly requests a refund → output: Refund
2. If the user wants to cancel their subscription or account → output: Cancellation
3. If the user mentions login, password, MFA, two-factor, or cannot access their account → output: Account Access
4. If the user mentions an invoice, charge, payment, pricing, or billing issue (and no higher-priority rule matches) → output: Billing
5. Otherwise → output: General Inquiry

IMPORTANT
---------
- Return ONLY the category string. No punctuation, no explanation, no extra words.
- Do not combine categories. Pick exactly one.

CONVERSATION
------------
User: {user_message}
Agent: {bot_response}

CATEGORY:"""


async def classify_trace(user_message: str, bot_response: str) -> str:
    """Classify a support conversation into exactly one Category value.

    Uses llama3 at temperature=0 for deterministic output.
    Falls back to 'General Inquiry' if the model returns an unrecognised string.

    Args:
        user_message: The message sent by the user.
        bot_response: The bot's reply to that message.

    Returns:
        A valid Category value string (e.g. "Billing", "Refund", …).
    """
    prompt = _CLASSIFICATION_PROMPT.format(
        user_message=user_message.strip(),
        bot_response=bot_response.strip(),
    )

    raw = await call_llama(
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
        num_predict=_CLASSIFY_NUM_PREDICT,
    )

    category = raw.strip().strip(".")

    if category in _VALID_CATEGORIES:
        return category

    # Try a case-insensitive match before falling back
    for valid in _VALID_CATEGORIES:
        if valid.lower() == category.lower():
            return valid

    logger.warning(
        "classify_trace: unexpected LLM output %r — defaulting to %r",
        raw,
        _DEFAULT_CATEGORY,
    )
    return _DEFAULT_CATEGORY
