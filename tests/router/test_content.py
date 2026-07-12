from datetime import date

from httpx import AsyncClient

from app.enums import ContentStatus, ContentType
from app.repository.mysql._models import ContentRecord


async def test_get_daily_content(client: AsyncClient, db_session) -> None:
    """해당 날짜에 예약(USED)된 콘텐츠를 반환한다."""
    record = ContentRecord(
        type=ContentType.QUOTE,
        status=ContentStatus.USED,
        content="Do or do not",
        used_at=date(2024, 1, 1),
    )
    db_session.add(record)
    await db_session.commit()

    response = await client.get("/api/v1/contents/", params={"date": "2024-01-01"})

    assert response.status_code == 200
    assert response.json()["content"]["id"] == record.id


async def test_get_daily_content_not_found(client: AsyncClient) -> None:
    """해당 날짜에 예약된 콘텐츠가 없으면 404를 반환한다."""
    response = await client.get("/api/v1/contents/", params={"date": "2024-01-01"})

    assert response.status_code == 404
