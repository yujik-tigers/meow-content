import base64
import logging
from abc import ABC, abstractmethod
from io import BytesIO
from typing import Any, override

from langchain.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.callbacks.manager import (
    AsyncCallbackManagerForLLMRun,
    CallbackManagerForLLMRun,
)
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_google_genai import ChatGoogleGenerativeAI
from openai import AsyncOpenAI
from openai.types import ImagesResponse
from PIL import Image as PILImage
from PIL.Image import Image
from pydantic import Field, model_validator

from app.enums import GptImageModel, NanoBananaModel

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
        self._llm = ChatGoogleGenerativeAI(
            model=model_name.value,
            image_config={"aspect_ratio": "1:1"},
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


class GptImage2(DiffusionModel):

    def __init__(self, model_name: GptImageModel) -> None:
        self._llm = _GptImage2ChatModel(model=model_name.value)

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


class _GptImage2ChatModel(BaseChatModel):
    """Thin LangChain wrapper around the OpenAI Images API for gpt-image-2.

    Calls images.generate/images.edit directly instead of going through a
    reasoning model's tool-call (Responses API `image_generation` tool).
    """

    model: str
    async_client: Any = Field(default=None, exclude=True)

    @model_validator(mode="after")
    def _init_clients(self) -> "_GptImage2ChatModel":
        self.async_client = AsyncOpenAI()
        return self

    @property
    @override
    def _llm_type(self) -> str:
        return "gpt-image-2"

    @override
    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        raise NotImplementedError("_GptImage2ChatModel only supports ainvoke")

    @override
    async def _agenerate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: AsyncCallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        prompt, image = self._extract_prompt_and_image(messages)

        if image is not None:
            response = await self.async_client.images.edit(
                model=self.model, image=self._image_to_file(*image), prompt=prompt
            )
        else:
            response = await self.async_client.images.generate(
                model=self.model, prompt=prompt
            )

        return ChatResult(
            generations=[
                ChatGeneration(message=self._images_response_to_ai_message(response))
            ]
        )

    def _extract_prompt_and_image(
        self,
        messages: list[BaseMessage],
    ) -> tuple[str, tuple[str, str] | None]:
        prompt_parts: list[str] = []
        image: tuple[str, str] | None = None

        for message in messages:
            content = message.content
            if isinstance(content, str):
                prompt_parts.append(content)
                continue

            for block in content:
                if not isinstance(block, dict):
                    continue
                if block["type"] == "text":
                    prompt_parts.append(block["text"])
                elif block["type"] == "image":
                    image = (block["base64"], block["mime_type"])

        return "\n".join(prompt_parts), image

    def _image_to_file(self, image_base64: str, mime: str) -> tuple[str, BytesIO, str]:
        return "image", BytesIO(base64.b64decode(image_base64)), mime

    def _images_response_to_ai_message(self, response: ImagesResponse) -> AIMessage:
        if not response.data or not response.data[0].b64_json:
            raise ValueError("No image data received from the model.")

        return AIMessage(
            content=[
                {
                    "type": "image",
                    "base64": response.data[0].b64_json,
                    "mime_type": "image/png",
                }
            ],
            response_metadata={"output_version": "v1"},
        )
