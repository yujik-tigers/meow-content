import logging
from collections.abc import Callable
from typing import Any

from langchain_core.callbacks import AsyncCallbackHandler
from langchain_core.messages import AIMessage
from langchain_core.outputs import LLMResult
from sqlmodel.ext.asyncio.session import AsyncSession

from app.repository.mysql.engine import AsyncSessionLocal
from app.repository.mysql.repository import MySQLTokenUsageRepository

logger = logging.getLogger(__name__)


class TokenUsageCallbackHandler(AsyncCallbackHandler):
    """Registered globally via register_configure_hook so every BaseChatModel
    call in the process is tracked automatically, regardless of which class
    constructs the model or how it's later wrapped (e.g. with_structured_output)."""

    def __init__(
        self, session_factory: Callable[[], AsyncSession] = AsyncSessionLocal
    ) -> None:
        super().__init__()
        self._session_factory = session_factory

    async def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        message = getattr(response.generations[0][0], "message", None)
        if not isinstance(message, AIMessage) or message.usage_metadata is None:
            return

        model = message.response_metadata.get("model_name", "unknown")
        usage = message.usage_metadata
        try:
            async with self._session_factory() as session:
                await MySQLTokenUsageRepository(session).record(
                    model, usage["input_tokens"], usage["output_tokens"]
                )
        except Exception:
            logger.exception("Failed to record token usage for model=%s", model)


token_usage_handler = TokenUsageCallbackHandler()
