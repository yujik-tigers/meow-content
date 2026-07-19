from datetime import datetime
from unittest.mock import MagicMock

import pytest
from langchain_core.runnables import RunnableLambda

from app.analyzer.literal_quote_analyzer import (
    LiteralQuoteAnalyzer,
    LiteralQuoteAnalyzeResult,
)
from app.enums import ContentStatus, ContentType, LiteralType
from app.schema.content import Content


@pytest.fixture
def movie_quote_analyzer() -> LiteralQuoteAnalyzer:
    return LiteralQuoteAnalyzer()


@pytest.fixture
def raw_movie_quote_content() -> Content:
    return Content(
        id=1,
        type=ContentType.LiteralQuote,
        status=ContentStatus.RAW,
        content="Here's looking at you, kid.",
        author="Rick Blaine",
        title="Casablanca",
        literal_type=LiteralType.MOVIE,
        created_at=datetime(2024, 1, 1),
    )


async def test_analyze_raw_content(
    movie_quote_analyzer: LiteralQuoteAnalyzer, raw_movie_quote_content: Content
) -> None:
    """RAW 영화 명대사를 LLM으로 분석하면 번역·표현·배경이 채워지고 ANALYZED 상태가 된다."""
    mock_result = LiteralQuoteAnalyzeResult(
        quote_translation="당신을 보고 있어요, 그대.",
        expression="looking at you",
        expression_translation="당신을 바라보다",
        background="영화 카사블랑카에서 릭이 일사에게 건네는 작별의 대사이다.",
    )

    mock_llm = MagicMock()
    mock_llm.with_structured_output.return_value = RunnableLambda(lambda _: mock_result)
    movie_quote_analyzer._llm = mock_llm

    result = await movie_quote_analyzer.analyze_raw_content(raw_movie_quote_content)

    assert result.content == raw_movie_quote_content.content
    assert result.content_translation == mock_result.quote_translation
    assert result.expression == mock_result.expression
    assert result.expression_translation == mock_result.expression_translation
    assert result.background == mock_result.background
    assert result.status == ContentStatus.ANALYZED
