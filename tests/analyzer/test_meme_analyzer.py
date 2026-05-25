from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.runnables import RunnableLambda
from pydantic import BaseModel

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
    mock_chain = AsyncMock()
    mock_chain.ainvoke.return_value = mock_result
    # Replace _chain on the plain Python instance
    meme_analyzer._chain = mock_chain

    result = await meme_analyzer.analyze_raw_content(raw_meme_content)

    assert result.content == "meme text"
    assert result.content_translation == "밈 번역"
    assert result.expression == "expression"
    assert result.expression_translation == "표현 번역"
    assert result.background == "배경 설명"
    assert result.status == ContentStatus.PENDING


async def test_reanalyze_content_fields(
    meme_analyzer: RedditMemeAnalyzer, raw_meme_content: Content
) -> None:
    """content field names → LLM field names (specific for meme) → back to content field names in result."""
    captured: dict[str, type[BaseModel]] = {}
    new_translation = "새로운 번역"
    new_expression = "turns out"

    async def fake_llm_fn(_: Any) -> MagicMock:
        mock = MagicMock()
        mock.model_dump.return_value = {
            "meme_text_translation": new_translation,
            "expressions": new_expression,
        }
        return mock

    def capture_and_return(model: type[BaseModel]) -> RunnableLambda:
        captured["model"] = model
        return RunnableLambda(fake_llm_fn)

    mock_llm = MagicMock()
    mock_llm.with_structured_output.side_effect = capture_and_return
    meme_analyzer._llm = mock_llm

    fields = [
        ReanalyzeContentField(
            field_name="content_translation", prompt_guide="formal tone"
        ),
        ReanalyzeContentField(field_name="expression", prompt_guide="자연스럽게"),
    ]
    result = await meme_analyzer.reanalyze_content_field(raw_meme_content, fields)

    # dynamic model fields must use LLM names, not content names
    model_field_names = set(captured["model"].model_fields.keys())
    assert "meme_text_translation" in model_field_names
    assert "expressions" in model_field_names

    assert "content_translation" not in model_field_names
    assert "expression" not in model_field_names

    assert (
        len(model_field_names) == 2
    )  # only requested fields are included in the LLM schema

    # LLM output is reverse-mapped to content field names in the returned Content
    assert result.content_translation == new_translation
    assert result.expression == new_expression
    assert (
        result.content == raw_meme_content.content
    )  # fields not included in the reanalysis request are preserved
    assert result.status == ContentStatus.PENDING
