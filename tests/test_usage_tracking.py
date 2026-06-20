from unittest.mock import AsyncMock, patch

from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, Generation, LLMResult

from app.usage.usage_tracking import TokenUsageCallbackHandler


def _llm_result(message) -> LLMResult:
    return LLMResult(generations=[[ChatGeneration(message=message)]])


async def test_on_llm_end_records_usage() -> None:
    message = AIMessage(
        content="hi",
        response_metadata={"model_name": "gpt-5.2"},
        usage_metadata={"input_tokens": 10, "output_tokens": 5, "total_tokens": 15},
    )
    mock_repository = AsyncMock()

    with (
        patch("app.usage.usage_tracking.AsyncSessionLocal") as mock_session_local,
        patch(
            "app.usage.usage_tracking.MySQLTokenUsageRepository", return_value=mock_repository
        ),
    ):
        mock_session_local.return_value.__aenter__.return_value = AsyncMock()
        handler = TokenUsageCallbackHandler()
        await handler.on_llm_end(_llm_result(message))

    mock_repository.record.assert_called_once_with("gpt-5.2", 10, 5)


async def test_on_llm_end_skips_when_no_usage_metadata() -> None:
    message = AIMessage(content="hi", response_metadata={"model_name": "gpt-5.2"})

    with patch("app.usage.usage_tracking.MySQLTokenUsageRepository") as mock_repository_cls:
        handler = TokenUsageCallbackHandler()
        await handler.on_llm_end(_llm_result(message))

    mock_repository_cls.assert_not_called()


async def test_on_llm_end_skips_non_chat_generation() -> None:
    result = LLMResult(generations=[[Generation(text="hi")]])

    with patch("app.usage.usage_tracking.MySQLTokenUsageRepository") as mock_repository_cls:
        handler = TokenUsageCallbackHandler()
        await handler.on_llm_end(result)

    mock_repository_cls.assert_not_called()


async def test_on_llm_end_swallows_repository_errors() -> None:
    message = AIMessage(
        content="hi",
        response_metadata={"model_name": "gpt-5.2"},
        usage_metadata={"input_tokens": 10, "output_tokens": 5, "total_tokens": 15},
    )

    with (
        patch("app.usage.usage_tracking.AsyncSessionLocal") as mock_session_local,
        patch(
            "app.usage.usage_tracking.MySQLTokenUsageRepository",
            side_effect=RuntimeError("boom"),
        ),
    ):
        mock_session_local.return_value.__aenter__.return_value = AsyncMock()
        handler = TokenUsageCallbackHandler()
        await handler.on_llm_end(_llm_result(message))
