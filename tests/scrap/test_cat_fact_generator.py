from unittest.mock import AsyncMock, MagicMock

from langchain_core.runnables import RunnableLambda

from app.enums import ContentType
from app.scrap.cat_fact_generator import CatFactBatch, CatFactGenerator


async def test_scrape_returns_new_content_for_each_generated_fact(mocker) -> None:
    """LLM이 생성한 각 fact가 FACT 타입 NewContent로 매핑되고 개별적으로 색인된다."""
    mock_batch = CatFactBatch(facts=["Cats have five toes.", "Cats purr at 25Hz."])

    mock_llm = MagicMock()
    mock_llm.with_structured_output.return_value = RunnableLambda(lambda _: mock_batch)
    generator = CatFactGenerator()
    generator._llm = mock_llm

    mocker.patch(
        "app.scrap.cat_fact_generator.cat_fact_similarity_repository.is_duplicate",
        new=AsyncMock(return_value=False),
    )
    mock_insert = mocker.patch(
        "app.scrap.cat_fact_generator.cat_fact_similarity_repository.insert",
        new=AsyncMock(),
    )

    result = await generator.scrape()

    assert len(result) == 2
    assert all(item.type == ContentType.FACT for item in result)
    assert result[0].content == "Cats have five toes."
    assert result[1].content == "Cats purr at 25Hz."
    assert mock_insert.call_count == 2


async def test_scrape_skips_facts_flagged_as_duplicates(mocker) -> None:
    """유사도 검사에서 중복으로 판정된 fact는 결과에서 제외되고 색인되지 않는다."""
    mock_batch = CatFactBatch(
        facts=["Duplicate fact.", "Fresh fact.", "Another duplicate."]
    )

    mock_llm = MagicMock()
    mock_llm.with_structured_output.return_value = RunnableLambda(lambda _: mock_batch)
    generator = CatFactGenerator()
    generator._llm = mock_llm

    mock_is_duplicate = AsyncMock(side_effect=[True, False, True])
    mocker.patch(
        "app.scrap.cat_fact_generator.cat_fact_similarity_repository.is_duplicate",
        new=mock_is_duplicate,
    )
    mock_insert = mocker.patch(
        "app.scrap.cat_fact_generator.cat_fact_similarity_repository.insert",
        new=AsyncMock(),
    )

    result = await generator.scrape()

    assert len(result) == 1
    assert result[0].content == "Fresh fact."
    assert mock_is_duplicate.call_count == 3
    mock_insert.assert_awaited_once_with("Fresh fact.")
