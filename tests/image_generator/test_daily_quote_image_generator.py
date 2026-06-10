from dataclasses import replace
from datetime import date, datetime
from unittest.mock import AsyncMock

import pytest
from PIL import Image as PILModule

from app.enums import ContentStatus, ContentType
from app.image_generator.daily_quote_image_generator import DailyQuoteImageGenerator
from app.image_generator.diffusion_model import DiffusionModel
from app.image_generator.s3_uploader import S3Client
from app.schema.content import Content
from app.settings import app_config

BUCKET_BASE = f"https://{app_config.AWS_S3_BUCKET_NAME}.s3.{app_config.AWS_REGION}.amazonaws.com"
TEST_DATE = date(2024, 1, 1)
TEST_TIMESTAMP = "240101120000"


@pytest.fixture
def mock_model():
    return AsyncMock(spec=DiffusionModel)


@pytest.fixture
def mock_s3():
    mock = AsyncMock(spec=S3Client)
    mock.upload_image.side_effect = lambda _, key: f"{BUCKET_BASE}/{key}"
    return mock


@pytest.fixture
def generator(mock_model, mock_s3):
    return DailyQuoteImageGenerator(mock_model, mock_s3)


@pytest.fixture
def pil_image():
    img = PILModule.new("RGB", (100, 100), "white")
    img.format = "PNG"
    return img


@pytest.fixture
def quote_content():
    return Content(
        id=1,
        type=ContentType.QUOTE,
        status=ContentStatus.ANALYZED,
        content="Life is short",
        author="Hippocrates",
        image_url=f"{BUCKET_BASE}/old.png",
        created_at=datetime(2024, 1, 1),
    )


async def test_generate_updates_image_url_and_status(
    generator, mock_model, quote_content, pil_image, mocker
):
    mock_model.create_image.return_value = pil_image
    mocker.patch(
        "app.image_generator.daily_quote_image_generator.image_text_renderer.add_text",
        return_value=pil_image,
    )
    mock_date = mocker.patch("app.image_generator.daily_quote_image_generator.date")
    mock_date.today.return_value = TEST_DATE

    result = await generator.generate(quote_content)

    expected_url = f"{BUCKET_BASE}/daily_quote/{TEST_DATE}/{quote_content.id}.png"
    assert result == replace(quote_content, image_url=expected_url, status=ContentStatus.PENDING)


async def test_regenerate_updates_image_url_and_status(
    generator, mock_model, mock_s3, quote_content, pil_image, mocker
):
    mock_s3.download_image.return_value = pil_image
    mock_model.recreate_image.return_value = pil_image
    mocker.patch(
        "app.image_generator.daily_quote_image_generator.image_text_renderer.add_text",
        return_value=pil_image,
    )
    mock_date = mocker.patch("app.image_generator.daily_quote_image_generator.date")
    mock_date.today.return_value = TEST_DATE
    mock_datetime = mocker.patch("app.image_generator.daily_quote_image_generator.datetime")
    mock_datetime.now.return_value.strftime.return_value = TEST_TIMESTAMP

    result = await generator.regenerate(quote_content, "make it darker")

    expected_url = f"{BUCKET_BASE}/daily_quote/{TEST_DATE}/{quote_content.id}/edited/{TEST_TIMESTAMP}.png"
    assert result == replace(quote_content, image_url=expected_url, status=ContentStatus.PENDING)
