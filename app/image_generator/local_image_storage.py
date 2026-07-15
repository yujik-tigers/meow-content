import asyncio
import io
from pathlib import Path

from PIL import Image as PILImage
from PIL.Image import Image

from app.image_generator.image_storage import ImageStorage
from app.settings import app_config

_CONTENT_TYPE_MAP = {
    "PNG": "image/png",
    "JPEG": "image/jpeg",
}


class LocalImageStorage(ImageStorage):
    def __init__(self) -> None:
        self._storage_dir = Path(app_config.IMAGE_STORAGE_DIR)
        self._base_url = app_config.MEDIA_BASE_URL

    async def upload_image(self, image: Image, image_name: str) -> str:
        fmt = image.format or "PNG"
        if fmt not in _CONTENT_TYPE_MAP:
            raise ValueError(f"Unsupported image format: {fmt}")

        image_data = io.BytesIO()
        image.save(image_data, format=fmt)
        image_bytes = image_data.getvalue()

        path = self._storage_dir / image_name

        def _write() -> None:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(image_bytes)

        await asyncio.get_running_loop().run_in_executor(None, _write)

        return f"{self._base_url}/{image_name}"

    async def download_image(self, image_url: str) -> Image:
        prefix = f"{self._base_url}/"
        if not image_url.startswith(prefix):
            raise ValueError(
                f"URL is not served from '{self._base_url}': {image_url}"
            )

        relative_path = image_url[len(prefix) :]
        path = self._storage_dir / relative_path

        def _read() -> bytes:
            return path.read_bytes()

        image_bytes = await asyncio.get_running_loop().run_in_executor(None, _read)

        return PILImage.open(io.BytesIO(image_bytes))
