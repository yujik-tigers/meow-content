from datetime import datetime
from typing import Any
from unittest.mock import MagicMock

import pytest
from langchain_core.runnables import RunnableLambda

from app.analyzer.daily_quote_analyzer import DailyQuoteAnalyzer, QuoteAnalyzeResult
from app.enums import ContentStatus, ContentType
from app.schema.content import Content, ReanalyzeContentField


@pytest.fixture
def quote_analyzer() -> DailyQuoteAnalyzer:
    return DailyQuoteAnalyzer()


@pytest.fixture
def raw_quote_content() -> Content:
    return Content(
        id=1,
        type=ContentType.QUOTE,
        status=ContentStatus.RAW,
        content="The only way to do great work is to love what you do.",
        author="Steve Jobs",
        created_at=datetime(2024, 1, 1),
    )


async def test_analyze_raw_content(
    quote_analyzer: DailyQuoteAnalyzer, raw_quote_content: Content
) -> None:
    mock_result = QuoteAnalyzeResult(
        quote_translation="위대한 일을 하는 유일한 방법은 자신이 하는 일을 사랑하는 것이다.",
        expression="love what you do",
        expression_translation="자신이 하는 일을 사랑하다",
        background="스티브 잡스가 스탠퍼드 졸업식 연설에서 한 말로, 열정을 따르는 삶의 중요성을 강조한다.",
    )

    mock_llm = MagicMock()
    mock_llm.with_structured_output.return_value = RunnableLambda(lambda _: mock_result)
    quote_analyzer._llm = mock_llm

    result = await quote_analyzer.analyze_raw_content(raw_quote_content)

    assert result.content == raw_quote_content.content
    assert result.content_translation == mock_result.quote_translation
    assert result.expression == mock_result.expression
    assert result.expression_translation == mock_result.expression_translation
    assert result.background == mock_result.background
    assert result.status == ContentStatus.ANALYZED


async def test_reanalyze_content_field(
    quote_analyzer: DailyQuoteAnalyzer, raw_quote_content: Content
) -> None:
    new_translation = "새로운 명언 번역"
    new_expression = "make a difference"

    def fake_result(_: Any) -> MagicMock:
        mock = MagicMock()
        mock.model_dump.return_value = {
            "quote_translation": new_translation,
            "expression": new_expression,
        }
        return mock

    mock_llm = MagicMock()
    mock_llm.with_structured_output.return_value = RunnableLambda(fake_result)
    quote_analyzer._llm = mock_llm

    fields = [
        ReanalyzeContentField(
            field_name="content_translation", prompt_guide="구어체로"
        ),
        ReanalyzeContentField(field_name="expression", prompt_guide="자연스럽게"),
    ]
    result = await quote_analyzer.reanalyze_content_field(raw_quote_content, fields)

    assert result.content_translation == new_translation
    assert result.expression == new_expression
    assert result.content == raw_quote_content.content
    assert result.status == ContentStatus.ANALYZED
