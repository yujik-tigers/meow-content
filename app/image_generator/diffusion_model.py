import base64
import logging
from abc import ABC, abstractmethod
from io import BytesIO
from typing import override

from google import genai
from google.genai import types
from openai import OpenAI
from openai.types import ImagesResponse
from PIL import Image as PILImage
from PIL.Image import Image

from app.enums import GptImageModel, NanoBananaModel

logger = logging.getLogger(__name__)


class DiffusionModel(ABC):

    @abstractmethod
    async def create_image(
        self,
        prompt: str,
    ) -> Image: ...

    @abstractmethod
    async def reinforce_image(self, prompt: str, previous_image: Image) -> Image: ...


class NanoBanana(DiffusionModel):

    def __init__(self, model_name: NanoBananaModel) -> None:
        self._model_name = model_name
        self._client = genai.Client()

    @override
    async def create_image(
        self,
        prompt: str,
    ) -> Image:
        response = self._client.models.generate_content(
            model=self._model_name.value,
            contents=[prompt],
        )

        return self._parse_image_from_response(response)

    @override
    async def reinforce_image(
        self,
        prompt: str,
        previous_image: Image,
    ) -> Image:
        response = self._client.models.generate_content(
            model=self._model_name.value,
            contents=[previous_image, prompt],
        )

        return self._parse_image_from_response(response)

    def _parse_image_from_response(
        self, response: types.GenerateContentResponse
    ) -> Image:
        image = None

        for part in response.parts or []:
            if part.text is not None:
                logging.info(f"Received text part: {part.text}")
            elif part.inline_data is not None:
                image = part.as_image()

        if image is None or image._pil_image is None:
            raise ValueError("No image data received from the model.")

        return image._pil_image


_FORMAT_MIME: dict[str, tuple[str, str]] = {
    "PNG": ("image.png", "image/png"),
    "JPEG": ("image.jpg", "image/jpeg"),
    "WEBP": ("image.webp", "image/webp"),
}


class GptImage2(DiffusionModel):

    def __init__(self, model_name: GptImageModel) -> None:
        self._model_name = model_name
        self._client = OpenAI()

    @override
    async def create_image(
        self,
        prompt: str,
    ) -> Image:
        result = self._client.images.generate(
            model=self._model_name.value, prompt=prompt
        )

        return self._parse_image_from_response(result)

    @override
    async def reinforce_image(
        self,
        prompt: str,
        previous_image: Image,
    ) -> Image:
        fmt = previous_image.format
        assert fmt is not None, "Image must have a format"
        filename, mime = _FORMAT_MIME[fmt]
        buffer = BytesIO()
        previous_image.save(buffer, format=fmt)
        buffer.seek(0)

        result = self._client.images.edit(
            model=self._model_name.value,
            image=(filename, buffer, mime),
            prompt=prompt,
        )
        return self._parse_image_from_response(result)

    def _parse_image_from_response(self, response: ImagesResponse) -> Image:
        if not response.data or not response.data[0].b64_json:
            raise ValueError("No image data received from the model.")

        return PILImage.open(BytesIO(base64.b64decode(response.data[0].b64_json)))
