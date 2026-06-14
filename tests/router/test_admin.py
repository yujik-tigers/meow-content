import dataclasses
from unittest.mock import AsyncMock

from httpx import AsyncClient

from app.enums import ContentStatus, RegenerateType
from app.exceptions import ContentNotFoundError
from app.schema.content import ReanalyzeContentField


async def test_generate_image_for_content(
    client: AsyncClient,
    mock_repository: AsyncMock,
    mock_image_generator: AsyncMock,
    make_content,
) -> None:
    content_id = 1
    content = make_content(id=content_id, status=ContentStatus.ANALYZED)
    generated = make_content(
        id=content_id,
        status=ContentStatus.PENDING,
        image_url="https://s3.example.com/gen.jpg",
    )

    mock_repository.get_content_by.return_value = content
    mock_image_generator.generate.return_value = generated

    response = await client.post(
        f"/api/v1/admin/contents/{content_id}/image",
        json={"model": "gpt-image-2-2026-04-21", "content_type": "quote"},
    )

    assert response.status_code == 200
    mock_repository.get_content_by.assert_called_once_with(content_id)
    mock_image_generator.generate.assert_called_once_with(content)
    mock_repository.update_content.assert_called_once_with(generated)


async def test_generate_image_content_not_found(
    client: AsyncClient, mock_repository: AsyncMock
) -> None:
    mock_repository.get_content_by.side_effect = ContentNotFoundError(999)

    response = await client.post(
        "/api/v1/admin/contents/999/image",
        json={"model": "gpt-image-2-2026-04-21", "content_type": "quote"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Content not found: 999"


async def test_regenerate_image_for_content(
    client: AsyncClient,
    mock_repository: AsyncMock,
    mock_image_generator: AsyncMock,
    make_content,
) -> None:
    content_id = 1
    prompt = "make it more vibrant"
    content = make_content(id=content_id, status=ContentStatus.PENDING)
    regenerated = make_content(
        id=content_id,
        status=ContentStatus.PENDING,
        image_url="https://s3.example.com/regen.jpg",
    )

    mock_repository.get_content_by.return_value = content
    mock_image_generator.regenerate.return_value = regenerated

    response = await client.post(
        f"/api/v1/admin/contents/{content_id}/image/regenerate",
        json={
            "prompt": prompt,
            "regenerate_type": "modify",
            "content_type": "quote",
            "model": "gpt-image-2-2026-04-21",
        },
    )

    assert response.status_code == 200
    mock_repository.get_content_by.assert_called_once_with(content_id)
    mock_image_generator.regenerate.assert_called_once_with(
        content, prompt, RegenerateType.MODIFY
    )
    mock_repository.update_content.assert_called_once_with(regenerated)


async def test_regenerate_image_content_not_found(
    client: AsyncClient, mock_repository: AsyncMock
) -> None:
    mock_repository.get_content_by.side_effect = ContentNotFoundError(999)

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


async def test_list_contents(
    client: AsyncClient, mock_repository: AsyncMock, make_content
) -> None:
    contents = [make_content(id=1), make_content(id=2)]
    mock_repository.fetch_contents_by.return_value = contents

    response = await client.get(
        "/api/v1/admin/contents",
        params={"content_status": "raw", "content_type": "reddit_meme"},
    )

    assert response.status_code == 200
    assert len(response.json()["content"]) == 2


async def test_list_contents_empty(
    client: AsyncClient, mock_repository: AsyncMock
) -> None:
    mock_repository.fetch_contents_by.return_value = []

    response = await client.get(
        "/api/v1/admin/contents",
        params={"content_status": "raw", "content_type": "reddit_meme"},
    )

    assert response.status_code == 200
    assert response.json()["content"] == []


async def test_analyze_content(
    client: AsyncClient,
    mock_repository: AsyncMock,
    mock_analyzer: AsyncMock,
    make_content,
) -> None:
    content_id = 1
    raw_content = make_content(status=ContentStatus.RAW)
    analyzed_content = make_content(status=ContentStatus.PENDING)

    mock_repository.get_content_by.return_value = raw_content
    mock_analyzer.analyze_raw_content.return_value = analyzed_content

    response = await client.post(
        f"/api/v1/admin/contents/{content_id}/analyze",
        content=b'"quote"',
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 200

    mock_repository.get_content_by.assert_called_once_with(content_id)
    mock_analyzer.analyze_raw_content.assert_called_once_with(raw_content)
    mock_repository.update_content.assert_called_once_with(analyzed_content)


async def test_analyze_content_not_found(
    client: AsyncClient, mock_repository: AsyncMock
) -> None:
    mock_repository.get_content_by.side_effect = ContentNotFoundError(999)

    response = await client.post(
        "/api/v1/admin/contents/999/analyze",
        content=b'"quote"',
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Content not found: 999"


async def test_update_status_valid(
    client: AsyncClient, mock_repository: AsyncMock
) -> None:
    response = await client.patch(
        "/api/v1/admin/contents/1/status",
        json={"from_status": "pending", "to_status": "approved"},
    )

    assert response.status_code == 204
    mock_repository.update_status.assert_called_once_with(1, ContentStatus.APPROVED)


async def test_update_status_invalid_transition(client: AsyncClient) -> None:
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
    mock_repository: AsyncMock,
    mock_analyzer: AsyncMock,
    make_content,
) -> None:
    content_id = 1
    content = make_content(status=ContentStatus.PENDING)
    updated = make_content(status=ContentStatus.PENDING, content_translation="새 번역")
    request = [
        ReanalyzeContentField(field_name="content_translation", prompt_guide="formal")
    ]

    mock_repository.get_content_by.return_value = content
    mock_analyzer.reanalyze_content_field.return_value = updated

    response = await client.patch(
        f"/api/v1/admin/contents/{content_id}",
        json={
            "request": [dataclasses.asdict(item) for item in request],
            "content_type": "quote",
        },
    )

    assert response.status_code == 204
    mock_repository.get_content_by.assert_called_once_with(content_id)
    mock_analyzer.reanalyze_content_field.assert_called_once_with(content, request)
    mock_repository.update_content.assert_called_once_with(updated)


async def test_reanalyze_fields_not_found(
    client: AsyncClient, mock_repository: AsyncMock
) -> None:
    mock_repository.get_content_by.side_effect = ContentNotFoundError(999)

    response = await client.patch(
        "/api/v1/admin/contents/999",
        json={
            "request": [{"field_name": "content_translation", "prompt_guide": ""}],
            "content_type": "quote",
        },
    )

    assert response.status_code == 404
