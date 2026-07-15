import io
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


def _png_bytes() -> bytes:
    buf = io.BytesIO()
    PILModule.new("RGB", (10, 10), "green").save(buf, format="PNG")
    return buf.getvalue()


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


async def test_download_image_returns_pil_image(s3_client):
    """S3 URL의 이미지를 내려받아 PIL 이미지로 반환한다."""
    mock_s3 = _setup_mock_s3(s3_client)
    mock_body = AsyncMock()
    mock_body.read.return_value = _png_bytes()
    mock_s3.get_object.return_value = {"Body": mock_body}

    url = f"{BASE_URL}/daily_quote/2024-01-01/1.png"
    result = await s3_client.download_image(url)

    assert isinstance(result, PILModule.Image)
    mock_s3.get_object.assert_called_once_with(
        Bucket=BUCKET, Key="daily_quote/2024-01-01/1.png"
    )


async def test_download_image_wrong_bucket_url_raises(s3_client):
    """다른 버킷의 URL로 다운로드를 요청하면 예외가 발생한다."""
    bad_url = "https://other-bucket.s3.us-east-1.amazonaws.com/image.png"
    with pytest.raises(ValueError, match="does not belong to bucket"):
        await s3_client.download_image(bad_url)


async def test_download_image_non_s3_url_raises(s3_client):
    """S3가 아닌 URL로 다운로드를 요청하면 예외가 발생한다."""
    bad_url = "https://example.com/image.png"
    with pytest.raises(ValueError, match="does not belong to bucket"):
        await s3_client.download_image(bad_url)
