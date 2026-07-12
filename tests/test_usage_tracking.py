from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, Generation, LLMResult
from sqlmodel import select

from app.repository.mysql._models import TokenUsageRecord
from app.usage.usage_tracking import TokenUsageCallbackHandler


def _llm_result(message) -> LLMResult:
    return LLMResult(generations=[[ChatGeneration(message=message)]])


def _usage_message() -> AIMessage:
    return AIMessage(
        content="hi",
        response_metadata={"model_name": "gpt-5.2"},
        usage_metadata={"input_tokens": 10, "output_tokens": 5, "total_tokens": 15},
    )


async def test_on_llm_end_records_usage(db_session_factory, db_session) -> None:
    """LLM 응답의 usage_metadata가 token_usage 테이블에 실제로 기록된다."""
    handler = TokenUsageCallbackHandler(session_factory=db_session_factory)

    await handler.on_llm_end(_llm_result(_usage_message()))

    rows = (await db_session.exec(select(TokenUsageRecord))).all()
    assert len(rows) == 1
    assert (rows[0].model, rows[0].input_tokens, rows[0].output_tokens) == (
        "gpt-5.2",
        10,
        5,
    )


async def test_on_llm_end_skips_when_no_usage_metadata(
    db_session_factory, db_session
) -> None:
    """usage_metadata가 없는 LLM 응답은 기록하지 않는다."""
    message = AIMessage(content="hi", response_metadata={"model_name": "gpt-5.2"})
    handler = TokenUsageCallbackHandler(session_factory=db_session_factory)

    await handler.on_llm_end(_llm_result(message))

    rows = (await db_session.exec(select(TokenUsageRecord))).all()
    assert rows == []


async def test_on_llm_end_skips_non_chat_generation(
    db_session_factory, db_session
) -> None:
    """chat 생성이 아닌 LLM 결과는 기록하지 않는다."""
    handler = TokenUsageCallbackHandler(session_factory=db_session_factory)

    await handler.on_llm_end(LLMResult(generations=[[Generation(text="hi")]]))

    rows = (await db_session.exec(select(TokenUsageRecord))).all()
    assert rows == []


async def test_on_llm_end_swallows_repository_errors() -> None:
    """토큰 기록이 실패해도 예외를 전파하지 않고 LLM 응답 흐름을 막지 않는다."""

    def _broken_factory():
        raise RuntimeError("boom")

    handler = TokenUsageCallbackHandler(session_factory=_broken_factory)

    await handler.on_llm_end(_llm_result(_usage_message()))
