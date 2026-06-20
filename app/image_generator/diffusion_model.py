import base64
import logging
from abc import ABC, abstractmethod
from io import BytesIO
from typing import override

from langchain.messages import AIMessage, HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from PIL import Image as PILImage
from PIL.Image import Image

from app.enums import NanoBananaModel

logger = logging.getLogger(__name__)


class DiffusionModel(ABC):

    _REINFORCE_SYSTEM_PROMPT = (
        "You are an image editing assistant. Edit the provided image according to "
        "the user's instructions and return only the edited image."
    )

    @abstractmethod
    async def create_image(
        self,
        prompt: str,
    ) -> Image: ...

    @abstractmethod
    async def reinforce_image(self, prompt: str, previous_image: Image) -> Image: ...

    def _image_to_base64(self, image: Image) -> tuple[str, str]:
        fmt = image.format
        assert fmt is not None, "Image must have a format"

        if fmt == "PNG":
            mime = "image/png"
        elif fmt == "JPEG":
            mime = "image/jpeg"
        else:
            raise ValueError(f"Unsupported image format: {fmt}")

        buffer = BytesIO()
        image.save(buffer, format=fmt)
        return base64.b64encode(buffer.getvalue()).decode("utf-8"), mime

    def _parse_image_from_response(self, response: AIMessage) -> Image:
        image = next(
            (item for item in response.content_blocks if item["type"] == "image"), None
        )
        image_base64 = image.get("base64") if image is not None else None
        if image_base64 is None:
            raise ValueError("No image data received from the model.")

        return PILImage.open(BytesIO(base64.b64decode(image_base64)))


class NanoBanana(DiffusionModel):

    def __init__(self, model_name: NanoBananaModel) -> None:
        self._llm = ChatGoogleGenerativeAI(model=model_name.value)

    @override
    async def create_image(
        self,
        prompt: str,
    ) -> Image:
        result = await self._llm.ainvoke(prompt)
        return self._parse_image_from_response(result)

    @override
    async def reinforce_image(
        self,
        prompt: str,
        previous_image: Image,
    ) -> Image:
        image_base64, mime = self._image_to_base64(previous_image)
        result = await self._llm.ainvoke(
            [
                SystemMessage(self._REINFORCE_SYSTEM_PROMPT),
                HumanMessage(
                    content=[
                        {"type": "text", "text": prompt},
                        {
                            "type": "image",
                            "base64": image_base64,
                            "mime_type": mime,
                        },
                    ]
                ),
            ]
        )

        return self._parse_image_from_response(result)


class GptImage2(DiffusionModel):

    def __init__(self) -> None:
        self._llm = ChatOpenAI(model="gpt-5.2").bind_tools(
            [{"type": "image_generation", "model": "gpt-image-2"}]
        )

    @override
    async def create_image(
        self,
        prompt: str,
    ) -> Image:
        result = await self._llm.ainvoke(prompt)

        return self._parse_image_from_response(result)

    @override
    async def reinforce_image(
        self,
        prompt: str,
        previous_image: Image,
    ) -> Image:
        image_base64, mime = self._image_to_base64(previous_image)

        result = await self._llm.ainvoke(
            [
                SystemMessage(self._REINFORCE_SYSTEM_PROMPT),
                HumanMessage(
                    content=[
                        {"type": "text", "text": prompt},
                        {
                            "type": "image",
                            "base64": image_base64,
                            "mime_type": mime,
                        },
                    ]
                ),
            ]
        )

        return self._parse_image_from_response(result)
