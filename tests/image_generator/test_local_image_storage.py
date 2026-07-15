from unittest.mock import MagicMock

import pytest
from PIL import Image as PILModule

from app.image_generator.local_image_storage import LocalImageStorage

BASE_URL = "http://localhost:8000/media"


@pytest.fixture
def storage(tmp_path, mocker):
    mocker.patch("app.image_generator.local_image_storage.app_config.IMAGE_STORAGE_DIR", str(tmp_path))
    mocker.patch("app.image_generator.local_image_storage.app_config.MEDIA_BASE_URL", BASE_URL)
    return LocalImageStorage()


def _png_image() -> PILModule.Image:
    img = PILModule.new("RGB", (10, 10), "red")
    img.format = "PNG"
    return img


def _jpeg_image() -> PILModule.Image:
    img = PILModule.new("RGB", (10, 10), "blue")
    img.format = "JPEG"
    return img


async def test_upload_png_returns_correct_url_and_writes_file(storage, tmp_path):
    """PNG 업로드 시 디스크에 파일을 쓰고 공개 URL을 반환한다."""
    url = await storage.upload_image(_png_image(), "daily_quote/2024-01-01/1.png")

    assert url == f"{BASE_URL}/daily_quote/2024-01-01/1.png"
    assert (tmp_path / "daily_quote/2024-01-01/1.png").exists()


async def test_upload_jpeg_returns_correct_url(storage, tmp_path):
    """JPEG 업로드도 동일하게 파일을 쓰고 공개 URL을 반환한다."""
    url = await storage.upload_image(_jpeg_image(), "photos/cat.jpg")

    assert url == f"{BASE_URL}/photos/cat.jpg"
    assert (tmp_path / "photos/cat.jpg").exists()


async def test_upload_unsupported_format_raises(storage):
    """지원하지 않는 이미지 포맷 업로드 요청은 예외가 발생한다."""
    img = MagicMock(spec=PILModule.Image)
    img.format = "BMP"

    with pytest.raises(ValueError, match="Unsupported image format"):
        await storage.upload_image(img, "image.bmp")


async def test_download_image_returns_pil_image(storage):
    """업로드했던 이미지를 URL로 다시 내려받아 PIL 이미지로 반환한다."""
    url = await storage.upload_image(_png_image(), "daily_quote/2024-01-01/1.png")

    result = await storage.download_image(url)

    assert isinstance(result, PILModule.Image)


async def test_download_image_non_matching_url_raises(storage):
    """저장소 base URL과 다른 URL로 다운로드를 요청하면 예외가 발생한다."""
    bad_url = "https://example.com/image.png"
    with pytest.raises(ValueError, match="is not served from"):
        await storage.download_image(bad_url)
