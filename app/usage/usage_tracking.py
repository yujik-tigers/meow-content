import logging
from typing import Any

from langchain_core.callbacks import AsyncCallbackHandler
from langchain_core.messages import AIMessage
from langchain_core.outputs import LLMResult

from app.repository.mysql.engine import AsyncSessionLocal
from app.repository.mysql.repository import MySQLTokenUsageRepository

logger = logging.getLogger(__name__)


class TokenUsageCallbackHandler(AsyncCallbackHandler):
    """Registered globally via register_configure_hook so every BaseChatModel
    call in the process is tracked automatically, regardless of which class
    constructs the model or how it's later wrapped (e.g. with_structured_output)."""

    async def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        message = getattr(response.generations[0][0], "message", None)
        if not isinstance(message, AIMessage) or message.usage_metadata is None:
            return

        model = message.response_metadata.get("model_name", "unknown")
        usage = message.usage_metadata
        try:
            async with AsyncSessionLocal() as session:
                await MySQLTokenUsageRepository(session).record(
                    model, usage["input_tokens"], usage["output_tokens"]
                )
        except Exception:
            logger.exception("Failed to record token usage for model=%s", model)


token_usage_handler = TokenUsageCallbackHandler()
