from unittest.mock import AsyncMock

from httpx import AsyncClient

from app.exceptions import NoApprovedContentError


async def test_get_daily_content(
    client: AsyncClient, mock_repository: AsyncMock, make_content
) -> None:
    content = make_content(id=1)
    mock_repository.get_reserved_content_at.return_value = content

    response = await client.get("/api/v1/contents/", params={"date": "2024-01-01"})

    assert response.status_code == 200
    assert response.json()["content"]["id"] == 1


async def test_get_daily_content_not_found(
    client: AsyncClient, mock_repository: AsyncMock
) -> None:
    mock_repository.get_reserved_content_at.side_effect = NoApprovedContentError()

    response = await client.get(
        "/api/v1/contents/",
        params={"date": "2024-01-01"},
    )

    assert response.status_code == 404
