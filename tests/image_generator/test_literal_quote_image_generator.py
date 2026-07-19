from dataclasses import replace
from datetime import date, datetime
from unittest.mock import AsyncMock

import pytest
from PIL import Image as PILModule

from app.enums import ContentStatus, ContentType, LiteralType
from app.image_generator.diffusion_model import DiffusionModel
from app.image_generator.literal_quote_image_generator import (
    LiteralQuoteImageGenerator,
)
from app.image_generator.s3_image_storage import S3ImageStorage
from app.schema.content import Content
from app.settings import app_config

BUCKET_BASE = (
    f"https://{app_config.AWS_S3_BUCKET_NAME}.s3.{app_config.AWS_REGION}.amazonaws.com"
)
TEST_DATE = date(2024, 1, 1)


@pytest.fixture
def mock_model():
    return AsyncMock(spec=DiffusionModel)


@pytest.fixture
def mock_s3():
    mock = AsyncMock(spec=S3ImageStorage)
    mock.upload_image.side_effect = lambda _, key: f"{BUCKET_BASE}/{key}"
    return mock


@pytest.fixture
def generator(mock_model, mock_s3):
    return LiteralQuoteImageGenerator(mock_model, mock_s3)


@pytest.fixture
def pil_image():
    img = PILModule.new("RGB", (100, 100), "white")
    img.format = "PNG"
    return img


@pytest.fixture
def movie_quote_content():
    return Content(
        id=1,
        type=ContentType.LiteralQuote,
        status=ContentStatus.ANALYZED,
        content="Here's looking at you, kid.",
        author="Rick Blaine",
        title="Casablanca",
        literal_type=LiteralType.MOVIE,
        image_url=f"{BUCKET_BASE}/old.png",
        created_at=datetime(2024, 1, 1),
    )


async def test_generate_updates_image_url_and_status(
    generator, mock_model, movie_quote_content, pil_image, mocker
):
    """이미지 생성 성공 시 literal_quote S3 키 규칙에 맞는 image_url과 PENDING 상태로 갱신된다."""
    mock_model.create_image.return_value = pil_image
    mocker.patch(
        "app.image_generator.literal_quote_image_generator.image_text_renderer.add_text",
        return_value=pil_image,
    )
    mock_date = mocker.patch("app.image_generator.literal_quote_image_generator.date")
    mock_date.today.return_value = TEST_DATE

    result = await generator.generate(movie_quote_content)

    expected_url = (
        f"{BUCKET_BASE}/literal_quote/{TEST_DATE}/{movie_quote_content.id}.png"
    )
    assert result == replace(
        movie_quote_content, image_url=expected_url, status=ContentStatus.PENDING
    )
