import io

import aioboto3
from PIL.Image import Image

from app.image_generator.image_storage import ImageStorage
from app.settings import app_config

_CONTENT_TYPE_MAP = {
    "PNG": "image/png",
    "JPEG": "image/jpeg",
}


class S3ImageStorage(ImageStorage):
    def __init__(self) -> None:
        self._session = aioboto3.Session(
            region_name=app_config.AWS_REGION,
            aws_access_key_id=app_config.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=app_config.AWS_SECRET_ACCESS_KEY,
        )
        self._bucket_name = app_config.AWS_S3_BUCKET_NAME
        self._region_name = app_config.AWS_REGION

    async def upload_image(self, image: Image, image_name: str) -> str:
        fmt = image.format or "PNG"
        content_type = _CONTENT_TYPE_MAP.get(fmt)
        if content_type is None:
            raise ValueError(f"Unsupported image format: {fmt}")

        image_data = io.BytesIO()
        image.save(image_data, format=fmt)
        image_data.seek(0)

        async with self._session.client("s3") as s3:  # type: ignore[attr-defined]
            await s3.put_object(
                Bucket=self._bucket_name,
                Key=image_name,
                Body=image_data,
                ContentType=content_type,
            )

        return f"https://{self._bucket_name}.s3.{self._region_name}.amazonaws.com/{image_name}"
