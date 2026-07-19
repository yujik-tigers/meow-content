from unittest.mock import AsyncMock, MagicMock

import pytest
from PIL import Image as PILModule

from app.image_generator.s3_image_storage import S3ImageStorage
from app.settings import app_config

BUCKET = app_config.AWS_S3_BUCKET_NAME
REGION = app_config.AWS_REGION
BASE_URL = f"https://{BUCKET}.s3.{REGION}.amazonaws.com"


@pytest.fixture
def s3_client(mocker):
    mocker.patch("app.image_generator.s3_image_storage.aioboto3.Session")
    return S3ImageStorage()


def _setup_mock_s3(s3_client) -> AsyncMock:
    """Return a mock s3 resource wired into the client's session context manager."""
    mock_s3 = AsyncMock()
    s3_client._session.client.return_value.__aenter__ = AsyncMock(return_value=mock_s3)
    s3_client._session.client.return_value.__aexit__ = AsyncMock(return_value=None)
    return mock_s3


def _png_image() -> PILModule.Image:
    img = PILModule.new("RGB", (10, 10), "red")
    img.format = "PNG"
    return img


def _jpeg_image() -> PILModule.Image:
    img = PILModule.new("RGB", (10, 10), "blue")
    img.format = "JPEG"
    return img


async def test_upload_png_returns_correct_url(s3_client):
    """PNG 업로드 시 올바른 ContentType·Key로 저장하고 공개 URL을 반환한다."""
    mock_s3 = _setup_mock_s3(s3_client)
    mock_s3.put_object = AsyncMock()

    url = await s3_client.upload_image(_png_image(), "daily_quote/2024-01-01/1.png")

    assert url == f"{BASE_URL}/daily_quote/2024-01-01/1.png"
    mock_s3.put_object.assert_called_once()
    call_kwargs = mock_s3.put_object.call_args.kwargs
    assert call_kwargs["ContentType"] == "image/png"
    assert call_kwargs["Key"] == "daily_quote/2024-01-01/1.png"
    assert call_kwargs["Bucket"] == BUCKET


async def test_upload_jpeg_returns_correct_url(s3_client):
    """JPEG 업로드 시 image/jpeg ContentType으로 저장하고 공개 URL을 반환한다."""
    mock_s3 = _setup_mock_s3(s3_client)
    mock_s3.put_object = AsyncMock()

    url = await s3_client.upload_image(_jpeg_image(), "photos/cat.jpg")

    assert url == f"{BASE_URL}/photos/cat.jpg"
    call_kwargs = mock_s3.put_object.call_args.kwargs
    assert call_kwargs["ContentType"] == "image/jpeg"


async def test_upload_unsupported_format_raises(s3_client):
    """지원하지 않는 이미지 포맷 업로드 요청은 예외가 발생한다."""
    img = MagicMock(spec=PILModule.Image)
    img.format = "BMP"

    with pytest.raises(ValueError, match="Unsupported image format"):
        await s3_client.upload_image(img, "image.bmp")
