import logging
from abc import ABC, abstractmethod
from typing import override

from google import genai
from google.genai import types
from PIL.Image import Image

from app.enums import NanoBananaModel

logger = logging.getLogger(__name__)


class DiffusionModel(ABC):

    @abstractmethod
    async def create_image(
        self,
        prompt: str,
    ) -> Image: ...

    @abstractmethod
    async def recreate_image(
        self,
        previous_image: Image,
        prompt: str,
    ) -> Image: ...


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
    async def recreate_image(
        self,
        previous_image: Image,
        prompt: str,
    ) -> Image:
        system_prompt = (
            "You are an image editing assistant. "
            "The user will provide an existing image and a description of the changes they want. "
            "Edit the image according to the instructions while preserving its overall composition and style. "
            "Return only the edited image."
        )

        response = self._client.models.generate_content(
            model=self._model_name.value,
            contents=[
                previous_image,
                prompt,
            ],
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
            ),
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
