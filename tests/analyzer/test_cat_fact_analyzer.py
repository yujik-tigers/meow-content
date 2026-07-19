from datetime import datetime
from typing import Any
from unittest.mock import MagicMock

from langchain_core.runnables import RunnableLambda

from app.analyzer.cat_fact_analyzer import CatFactAnalyzeResult, CatFactAnalyzer
from app.enums import ContentStatus, ContentType
from app.schema.content import Content, ReanalyzeContentField


def _fact_analyzer() -> CatFactAnalyzer:
    return CatFactAnalyzer()


def _raw_fact_content() -> Content:
    return Content(
        id=1,
        type=ContentType.FACT,
        status=ContentStatus.RAW,
        content="Cats have five toes on their front paws.",
        created_at=datetime(2024, 1, 1),
    )


async def test_analyze_raw_content() -> None:
    """RAW fact를 LLM으로 분석하면 번역·배경이 채워지고 ANALYZED 상태가 된다."""
    fact_analyzer = _fact_analyzer()
    raw_fact_content = _raw_fact_content()
    mock_result = CatFactAnalyzeResult(
        fact_translation="고양이는 앞발에 발가락이 다섯 개 있다.",
        background="고양이의 앞발과 뒷발은 발가락 수가 다르다는 점이 흥미롭다.",
    )

    mock_llm = MagicMock()
    mock_llm.with_structured_output.return_value = RunnableLambda(lambda _: mock_result)
    fact_analyzer._llm = mock_llm

    result = await fact_analyzer.analyze_raw_content(raw_fact_content)

    assert result.content == raw_fact_content.content
    assert result.content_translation == mock_result.fact_translation
    assert result.background == mock_result.background
    assert result.status == ContentStatus.ANALYZED


async def test_reanalyze_content_field() -> None:
    """요청한 필드만 프롬프트 가이드에 따라 재분석되어 갱신된다."""
    fact_analyzer = _fact_analyzer()
    raw_fact_content = _raw_fact_content()
    new_translation = "새로운 팩트 번역"
    new_background = "새로운 배경 설명"

    def fake_result(_: Any) -> MagicMock:
        mock = MagicMock()
        mock.model_dump.return_value = {
            "fact_translation": new_translation,
            "background": new_background,
        }
        return mock

    mock_llm = MagicMock()
    mock_llm.with_structured_output.return_value = RunnableLambda(fake_result)
    fact_analyzer._llm = mock_llm

    fields = [
        ReanalyzeContentField(field_name="content_translation", prompt_guide="구어체로"),
        ReanalyzeContentField(field_name="background", prompt_guide="간결하게"),
    ]
    result = await fact_analyzer.reanalyze_content_field(raw_fact_content, fields)

    assert result.content_translation == new_translation
    assert result.background == new_background
    assert result.content == raw_fact_content.content
    assert result.status == ContentStatus.ANALYZED
