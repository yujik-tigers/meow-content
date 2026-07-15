import dataclasses
from datetime import datetime
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient
from sqlmodel import select

from app.enums import ContentStatus, ContentType, RegenerateType
from app.repository.mysql._models import ContentRecord, TokenUsageRecord
from app.schema.content import NewContent, ReanalyzeContentField


async def _seed_content(db_session, **kwargs) -> ContentRecord:
    record = ContentRecord(**kwargs)
    db_session.add(record)
    await db_session.commit()
    return record


async def test_generate_image_for_content(
    client: AsyncClient,
    db_session,
    mock_image_generator: AsyncMock,
    make_content,
) -> None:
    """이미지 생성 요청 시 생성기가 반환한 image_url·상태가 DB에 반영된다."""
    record = await _seed_content(
        db_session,
        type=ContentType.QUOTE,
        status=ContentStatus.ANALYZED,
        content="quote",
    )
    mock_image_generator.generate.return_value = make_content(
        id=record.id,
        type=ContentType.QUOTE,
        status=ContentStatus.PENDING,
        image_url="https://s3.example.com/gen.jpg",
    )

    response = await client.post(
        f"/api/v1/admin/contents/{record.id}/image",
        json={"model": "gpt-image-2-2026-04-21", "content_type": "quote"},
    )

    assert response.status_code == 200
    assert mock_image_generator.generate.call_args.args[0].id == record.id
    await db_session.refresh(record)
    assert record.image_url == "https://s3.example.com/gen.jpg"
    assert record.status == ContentStatus.PENDING


async def test_generate_image_content_not_found(client: AsyncClient) -> None:
    """존재하지 않는 콘텐츠의 이미지 생성 요청은 404를 반환한다."""
    response = await client.post(
        "/api/v1/admin/contents/999/image",
        json={"model": "gpt-image-2-2026-04-21", "content_type": "quote"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Content not found: 999"


async def test_regenerate_image_for_content(
    client: AsyncClient,
    db_session,
    mock_image_generator: AsyncMock,
    make_content,
) -> None:
    """이미지 재생성 요청 시 프롬프트가 생성기에 전달되고 결과가 DB에 반영된다."""
    prompt = "make it more vibrant"
    record = await _seed_content(
        db_session,
        type=ContentType.QUOTE,
        status=ContentStatus.PENDING,
        content="quote",
        image_url="https://s3.example.com/old.jpg",
    )
    mock_image_generator.regenerate.return_value = make_content(
        id=record.id,
        type=ContentType.QUOTE,
        status=ContentStatus.PENDING,
        image_url="https://s3.example.com/regen.jpg",
    )

    response = await client.post(
        f"/api/v1/admin/contents/{record.id}/image/regenerate",
        json={
            "prompt": prompt,
            "regenerate_type": "modify",
            "content_type": "quote",
            "model": "gpt-image-2-2026-04-21",
        },
    )

    assert response.status_code == 200
    called_content, called_prompt, called_type = (
        mock_image_generator.regenerate.call_args.args
    )
    assert called_content.id == record.id
    assert called_prompt == prompt
    assert called_type == RegenerateType.MODIFY
    await db_session.refresh(record)
    assert record.image_url == "https://s3.example.com/regen.jpg"


async def test_regenerate_image_content_not_found(client: AsyncClient) -> None:
    """존재하지 않는 콘텐츠의 이미지 재생성 요청은 404를 반환한다."""
    response = await client.post(
        "/api/v1/admin/contents/999/image/regenerate",
        json={
            "prompt": "test",
            "regenerate_type": "modify",
            "content_type": "quote",
            "model": "gpt-image-2-2026-04-21",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Content not found: 999"


async def test_list_contents(client: AsyncClient, db_session) -> None:
    """상태·타입 필터에 맞는 콘텐츠 목록을 반환한다."""
    await _seed_content(
        db_session,
        type=ContentType.REDDIT_MEME,
        status=ContentStatus.RAW,
        image_url="https://i.redd.it/cat1.jpg",
    )
    await _seed_content(
        db_session,
        type=ContentType.REDDIT_MEME,
        status=ContentStatus.RAW,
        image_url="https://i.redd.it/cat2.jpg",
    )
    await _seed_content(
        db_session, type=ContentType.QUOTE, status=ContentStatus.RAW, content="q"
    )

    response = await client.get(
        "/api/v1/admin/contents",
        params={"content_status": "raw", "content_type": "reddit_meme"},
    )

    assert response.status_code == 200
    body = response.json()["content"]
    assert len(body) == 2
    assert {item["image_url"] for item in body} == {
        "https://i.redd.it/cat1.jpg",
        "https://i.redd.it/cat2.jpg",
    }


async def test_list_contents_empty(client: AsyncClient) -> None:
    """조건에 맞는 콘텐츠가 없으면 빈 목록을 반환한다."""
    response = await client.get(
        "/api/v1/admin/contents",
        params={"content_status": "raw", "content_type": "reddit_meme"},
    )

    assert response.status_code == 200
    assert response.json()["content"] == []


async def test_analyze_content(
    client: AsyncClient,
    db_session,
    mock_analyzer: AsyncMock,
    make_content,
) -> None:
    """콘텐츠 분석 요청 시 분석 결과 필드가 DB에 반영된다."""
    record = await _seed_content(
        db_session,
        type=ContentType.QUOTE,
        status=ContentStatus.RAW,
        content="Do or do not",
    )
    mock_analyzer.analyze_raw_content.return_value = make_content(
        id=record.id,
        type=ContentType.QUOTE,
        status=ContentStatus.ANALYZED,
        content="Do or do not",
        content_translation="하거나 하지 않거나",
    )

    response = await client.post(
        f"/api/v1/admin/contents/{record.id}/analyze",
        content=b'"quote"',
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 200
    assert mock_analyzer.analyze_raw_content.call_args.args[0].id == record.id
    await db_session.refresh(record)
    assert record.status == ContentStatus.ANALYZED
    assert record.content_translation == "하거나 하지 않거나"


async def test_analyze_content_not_found(client: AsyncClient) -> None:
    """존재하지 않는 콘텐츠의 분석 요청은 404를 반환한다."""
    response = await client.post(
        "/api/v1/admin/contents/999/analyze",
        content=b'"quote"',
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Content not found: 999"


async def _seed_usage(db_session) -> None:
    db_session.add_all(
        [
            TokenUsageRecord(
                model="gpt-5.2",
                input_tokens=500,
                output_tokens=250,
                created_at=datetime(2026, 6, 15, 10, 0),
            ),
            TokenUsageRecord(
                model="gpt-5.2",
                input_tokens=500,
                output_tokens=250,
                created_at=datetime(2026, 6, 15, 14, 0),
            ),
            TokenUsageRecord(
                model="unknown-model",
                input_tokens=10,
                output_tokens=10,
                created_at=datetime(2026, 6, 15, 11, 0),
            ),
        ]
    )
    await db_session.commit()


async def test_get_usage_cost(client: AsyncClient, db_session) -> None:
    """기간 내 실제 사용량 집계로 모델별 비용을 계산하고, 모르는 모델은 비용 없음으로 반환한다."""
    await _seed_usage(db_session)

    response = await client.get(
        "/api/v1/admin/usage/cost",
        params={"start": "2026-06-01T00:00:00", "end": "2026-07-01T00:00:00"},
    )

    assert response.status_code == 200
    body = response.json()["content"]
    assert len(body) == 2
    by_model = {item["model"]: item for item in body}
    assert by_model["gpt-5.2"]["request_count"] == 2
    assert by_model["gpt-5.2"]["cost"] is not None
    assert by_model["unknown-model"]["cost"] is None


async def test_get_usage_cost_applies_free_tier(
    client: AsyncClient, db_session
) -> None:
    """무료 티어 적용 시 일일 무료 한도를 차감한 초과분만 과금된다."""
    db_session.add(
        TokenUsageRecord(
            model="gpt-5.2",
            input_tokens=1_000_000,
            output_tokens=0,
            created_at=datetime(2026, 6, 15, 12, 0),
        )
    )
    await db_session.commit()

    response = await client.get(
        "/api/v1/admin/usage/cost",
        params={
            "start": "2026-06-15T00:00:00",
            "end": "2026-06-16T00:00:00",
            "apply_free_tier": True,
        },
    )

    assert response.status_code == 200
    body = response.json()["content"]
    # billable = 1_000_000 - 250_000 (daily free tier) = 750_000
    assert body[0]["cost"] == pytest.approx(750_000 * 1.75 / 1_000_000)


async def test_update_status_valid(client: AsyncClient, db_session) -> None:
    """PENDING 콘텐츠 상태 변경 요청 시 DB의 상태가 APPROVED로 갱신된다."""
    record = await _seed_content(
        db_session,
        type=ContentType.QUOTE,
        status=ContentStatus.PENDING,
        content="quote",
    )

    response = await client.patch(
        f"/api/v1/admin/contents/{record.id}/status",
        json={"from_status": "pending", "to_status": "approved"},
    )

    assert response.status_code == 204
    await db_session.refresh(record)
    assert record.status == ContentStatus.APPROVED


async def test_update_status_invalid_transition(client: AsyncClient) -> None:
    """허용되지 않는 상태 전이 요청은 422 검증 에러를 반환한다."""
    response = await client.patch(
        "/api/v1/admin/contents/1/status",
        json={"from_status": "raw", "to_status": "approved"},
    )

    assert response.status_code == 422
    assert (
        response.json()["detail"][0]["msg"]
        == "Value error, Cannot transition to approved from raw: from_status must be PENDING"
    )


async def test_reanalyze_fields(
    client: AsyncClient,
    db_session,
    mock_analyzer: AsyncMock,
    make_content,
) -> None:
    """특정 필드 재분석 요청 시 재분석 결과가 DB에 반영된다."""
    record = await _seed_content(
        db_session,
        type=ContentType.QUOTE,
        status=ContentStatus.PENDING,
        content="quote",
        content_translation="이전 번역",
    )
    request = [
        ReanalyzeContentField(field_name="content_translation", prompt_guide="formal")
    ]
    mock_analyzer.reanalyze_content_field.return_value = make_content(
        id=record.id,
        type=ContentType.QUOTE,
        status=ContentStatus.PENDING,
        content_translation="새 번역",
    )

    response = await client.patch(
        f"/api/v1/admin/contents/{record.id}",
        json={
            "request": [dataclasses.asdict(item) for item in request],
            "content_type": "quote",
        },
    )

    assert response.status_code == 204
    called_content, called_request = (
        mock_analyzer.reanalyze_content_field.call_args.args
    )
    assert called_content.id == record.id
    assert called_request == request
    await db_session.refresh(record)
    assert record.content_translation == "새 번역"


async def test_reanalyze_fields_not_found(client: AsyncClient) -> None:
    """존재하지 않는 콘텐츠의 재분석 요청은 404를 반환한다."""
    response = await client.patch(
        "/api/v1/admin/contents/999",
        json={
            "request": [{"field_name": "content_translation", "prompt_guide": ""}],
            "content_type": "quote",
        },
    )

    assert response.status_code == 404


async def test_trigger_scraping(
    client: AsyncClient, db_session, mock_scraper: AsyncMock
) -> None:
    """스크래핑 트리거 요청 시 선택된 타입의 스크래퍼가 실행되고 결과가 RAW로 저장된다."""
    mock_scraper.scrape.return_value = [
        NewContent(
            type=ContentType.REDDIT_MEME,
            image_url="https://i.redd.it/cat.jpg",
            author="user1",
            title="Cat",
        )
    ]

    response = await client.post(
        "/api/v1/admin/scrap", json={"content_type": "reddit_meme"}
    )

    assert response.status_code == 204
    mock_scraper.scrape.assert_awaited_once()
    rows = (await db_session.exec(select(ContentRecord))).all()
    assert len(rows) == 1
    assert rows[0].status == ContentStatus.RAW
    assert rows[0].image_url == "https://i.redd.it/cat.jpg"
