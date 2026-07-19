from dataclasses import replace
from datetime import date, datetime
from unittest.mock import AsyncMock

import pytest
from PIL import Image as PILModule

from app.enums import ContentStatus, ContentType, RegenerateType
from app.image_generator.diffusion_model import DiffusionModel
from app.image_generator.cat_fact_image_generator import CatFactImageGenerator
from app.image_generator.s3_image_storage import S3ImageStorage
from app.schema.content import Content
from app.settings import app_config

BUCKET_BASE = (
    f"https://{app_config.AWS_S3_BUCKET_NAME}.s3.{app_config.AWS_REGION}.amazonaws.com"
)
TEST_DATE = date(2024, 1, 1)
TEST_TIMESTAMP = "240101120000"


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
    return CatFactImageGenerator(mock_model, mock_s3)


@pytest.fixture
def pil_image():
    img = PILModule.new("RGB", (100, 100), "white")
    img.format = "PNG"
    return img


@pytest.fixture
def fact_content():
    return Content(
        id=1,
        type=ContentType.FACT,
        status=ContentStatus.ANALYZED,
        content="Cats have five toes on their front paws.",
        image_url=f"{BUCKET_BASE}/old.png",
        created_at=datetime(2024, 1, 1),
    )


async def test_generate_updates_image_url_and_status(
    generator, mock_model, fact_content, pil_image, mocker
):
    """이미지 생성 성공 시 fact S3 키 규칙에 맞는 image_url과 PENDING 상태로 갱신된다."""
    mock_model.create_image.return_value = pil_image
    mock_add_text = mocker.patch(
        "app.image_generator.cat_fact_image_generator.image_text_renderer.add_text",
        return_value=pil_image,
    )
    mock_date = mocker.patch("app.image_generator.cat_fact_image_generator.date")
    mock_date.today.return_value = TEST_DATE

    result = await generator.generate(fact_content)

    expected_url = f"{BUCKET_BASE}/fact/{TEST_DATE}/{fact_content.id}.png"
    assert result == replace(
        fact_content, image_url=expected_url, status=ContentStatus.PENDING
    )
    mock_add_text.assert_called_once_with(pil_image, fact_content.content)


async def test_regenerate_updates_image_url_and_status(
    generator, mock_model, mock_s3, fact_content, pil_image, mocker
):
    """이미지 재생성 시 기존 이미지를 내려받아 보강하고 edited 경로의 image_url로 갱신된다."""
    mock_s3.download_image.return_value = pil_image
    mock_model.reinforce_image.return_value = pil_image
    mock_add_text = mocker.patch(
        "app.image_generator.cat_fact_image_generator.image_text_renderer.add_text",
        return_value=pil_image,
    )
    mock_date = mocker.patch("app.image_generator.cat_fact_image_generator.date")
    mock_date.today.return_value = TEST_DATE
    mock_datetime = mocker.patch("app.image_generator.cat_fact_image_generator.datetime")
    mock_datetime.now.return_value.strftime.return_value = TEST_TIMESTAMP

    result = await generator.regenerate(
        fact_content, "make it darker", RegenerateType.MODIFY
    )

    expected_url = (
        f"{BUCKET_BASE}/fact/{TEST_DATE}/{fact_content.id}/edited/{TEST_TIMESTAMP}.png"
    )
    assert result == replace(
        fact_content, image_url=expected_url, status=ContentStatus.PENDING
    )
    mock_add_text.assert_called_once_with(pil_image, fact_content.content)
