from datetime import datetime
from typing import Any
from unittest.mock import MagicMock

import pytest
from langchain_core.runnables import RunnableLambda

from app.analyzer.meme_analyzer import MemeAnalyzeResult, RedditMemeAnalyzer
from app.enums import ContentStatus, ContentType
from app.schema.content import Content, ReanalyzeContentField


@pytest.fixture
def meme_analyzer() -> RedditMemeAnalyzer:
    return RedditMemeAnalyzer()


@pytest.fixture
def raw_meme_content() -> Content:
    return Content(
        id=1,
        type=ContentType.REDDIT_MEME,
        status=ContentStatus.RAW,
        content="original text",
        content_translation="원본 번역",
        expression="turns out",
        expression_translation="알고 보니",
        background="배경",
        created_at=datetime(2024, 1, 1),
        image_url="https://example.com/cat.jpg",
    )


async def test_analyze_raw_content(
    meme_analyzer: RedditMemeAnalyzer, raw_meme_content: Content
) -> None:
    mock_result = MemeAnalyzeResult(
        meme_text="meme text",
        meme_text_translation="밈 번역",
        expressions="expression",
        translation="표현 번역",
        background="배경 설명",
    )

    mock_llm = MagicMock()
    mock_llm.with_structured_output.return_value = RunnableLambda(lambda _: mock_result)
    meme_analyzer._llm = mock_llm

    result = await meme_analyzer.analyze_raw_content(raw_meme_content)

    assert result.content == mock_result.meme_text
    assert result.content_translation == mock_result.meme_text_translation
    assert result.expression == mock_result.expressions
    assert result.expression_translation == mock_result.translation
    assert result.background == mock_result.background
    assert result.status == ContentStatus.PENDING


async def test_reanalyze_content_field(
    meme_analyzer: RedditMemeAnalyzer, raw_meme_content: Content
) -> None:
    new_translation = "새로운 번역"
    new_expression = "turns out"

    def fake_result(_: Any) -> MagicMock:
        mock = MagicMock()
        mock.model_dump.return_value = {
            "meme_text_translation": new_translation,
            "expressions": new_expression,
        }
        return mock

    mock_llm = MagicMock()
    mock_llm.with_structured_output.return_value = RunnableLambda(fake_result)
    meme_analyzer._llm = mock_llm

    fields = [
        ReanalyzeContentField(field_name="content_translation", prompt_guide="formal tone"),
        ReanalyzeContentField(field_name="expression", prompt_guide="자연스럽게"),
    ]
    result = await meme_analyzer.reanalyze_content_field(raw_meme_content, fields)

    assert result.content_translation == new_translation
    assert result.expression == new_expression
    assert result.content == raw_meme_content.content
    assert result.status == ContentStatus.PENDING
