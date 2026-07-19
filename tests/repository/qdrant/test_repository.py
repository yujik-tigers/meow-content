from unittest.mock import AsyncMock, MagicMock

import pytest

from app.repository.qdrant.repository import CatFactSimilarityRepository
from app.settings import app_config


def _make_embedding_response(
    vector: list[float], prompt_tokens: int = 5, total_tokens: int = 5
) -> MagicMock:
    response = MagicMock()
    response.data = [MagicMock(embedding=vector)]
    response.usage = MagicMock(prompt_tokens=prompt_tokens, total_tokens=total_tokens)
    return response


@pytest.fixture
def repository(mocker) -> CatFactSimilarityRepository:
    mocker.patch("app.repository.qdrant.repository.AsyncOpenAI")
    return CatFactSimilarityRepository()


async def test_is_duplicate_returns_false_when_no_similar_content(
    repository, mocker
) -> None:
    """유사한 기존 fact가 전혀 없으면 False를 반환한다."""
    repository._embedder.async_client.embeddings.create = AsyncMock(
        return_value=_make_embedding_response([0.1, 0.2, 0.3])
    )
    mock_query_points = mocker.patch(
        "app.repository.qdrant.repository.qdrant_client.query_points",
        new=AsyncMock(return_value=MagicMock(points=[])),
    )

    result = await repository.is_duplicate("Cats have five toes.")

    assert result is False
    mock_query_points.assert_awaited_once()


async def test_is_duplicate_returns_true_when_similarity_at_or_above_threshold(
    repository, mocker
) -> None:
    """유사도 임계값 이상인 기존 fact가 있으면 True를 반환한다."""
    repository._embedder.async_client.embeddings.create = AsyncMock(
        return_value=_make_embedding_response([0.1, 0.2, 0.3])
    )
    matched_point = MagicMock(
        score=app_config.FACT_SIMILARITY_THRESHOLD, payload={"content": "Known fact."}
    )
    mocker.patch(
        "app.repository.qdrant.repository.qdrant_client.query_points",
        new=AsyncMock(return_value=MagicMock(points=[matched_point])),
    )

    result = await repository.is_duplicate("Cats have five toes.")

    assert result is True


async def test_is_duplicate_returns_false_when_below_similarity_threshold(
    repository, mocker
) -> None:
    """유사도가 임계값보다 낮은 기존 fact만 있으면 False를 반환한다."""
    repository._embedder.async_client.embeddings.create = AsyncMock(
        return_value=_make_embedding_response([0.1, 0.2, 0.3])
    )
    below_threshold_point = MagicMock(score=app_config.FACT_SIMILARITY_THRESHOLD - 0.1)
    mocker.patch(
        "app.repository.qdrant.repository.qdrant_client.query_points",
        new=AsyncMock(return_value=MagicMock(points=[below_threshold_point])),
    )

    result = await repository.is_duplicate("Cats have five toes.")

    assert result is False


async def test_insert_upserts_embedding_with_payload(repository, mocker) -> None:
    """insert는 임베딩과 원문을 payload에 담아 Qdrant에 upsert한다."""
    vector = [0.1, 0.2, 0.3]
    repository._embedder.async_client.embeddings.create = AsyncMock(
        return_value=_make_embedding_response(vector)
    )
    mock_upsert = mocker.patch(
        "app.repository.qdrant.repository.qdrant_client.upsert", new=AsyncMock()
    )

    await repository.insert("Cats have five toes.")

    mock_upsert.assert_awaited_once()
    _, upsert_kwargs = mock_upsert.await_args
    assert upsert_kwargs["points"][0].vector == vector
    assert upsert_kwargs["points"][0].payload == {"content": "Cats have five toes."}


async def test_embed_carries_usage_metadata_for_token_tracking(repository) -> None:
    """임베딩 응답의 usage가 usage_metadata로 변환되어 전역 토큰 사용량 추적에 활용될 수 있다."""
    vector = [0.4, 0.5]
    repository._embedder.async_client.embeddings.create = AsyncMock(
        return_value=_make_embedding_response(vector, prompt_tokens=7, total_tokens=7)
    )

    result = await repository._embedder.ainvoke("Cats have five toes.")

    assert result.usage_metadata is not None
    assert result.usage_metadata["input_tokens"] == 7
    assert result.usage_metadata["output_tokens"] == 0
    assert result.response_metadata["embedding"] == vector
