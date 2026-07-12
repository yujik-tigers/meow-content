import base64
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain.messages import AIMessage
from PIL import Image as PILModule

from app.enums import GptImageModel, NanoBananaModel
from app.image_generator.diffusion_model import GptImage2, NanoBanana


def _make_image_base64(fmt: str = "PNG") -> str:
    buffer = BytesIO()
    PILModule.new("RGB", (1, 1), "blue").save(buffer, format=fmt)
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def _make_image_response(mime_type: str = "image/png") -> AIMessage:
    return AIMessage(
        content=[
            {
                "type": "image",
                "base64": _make_image_base64(),
                "mime_type": mime_type,
            }
        ],
        response_metadata={"output_version": "v1"},
    )


def _make_images_response(b64_json: str | None, usage: MagicMock | None = None) -> MagicMock:
    response = MagicMock()
    response.data = [MagicMock(b64_json=b64_json)] if b64_json is not None else []
    response.usage = usage
    return response


def _make_previous_image(fmt: str = "PNG") -> PILModule.Image:
    image = PILModule.new("RGB", (10, 10), "red")
    image.format = fmt
    return image


@pytest.fixture
def nano_banana(mocker):
    mocker.patch("app.image_generator.diffusion_model.ChatGoogleGenerativeAI")
    return NanoBanana(NanoBananaModel.NANO_BANANA_2)


@pytest.fixture
def gpt_image2(mocker):
    mocker.patch("app.image_generator.diffusion_model.AsyncOpenAI")
    return GptImage2(GptImageModel.GPT_IMAGE_2)


async def test_nano_banana_create_image_parses_image_from_response(nano_banana):
    """Nano Banana(Gemini) 응답의 이미지 데이터를 PIL 이미지로 파싱한다."""
    nano_banana._llm.ainvoke = AsyncMock(return_value=_make_image_response())

    result = await nano_banana.create_image("a cat sitting on a couch")

    assert isinstance(result, PILModule.Image)


async def test_nano_banana_reinforce_image_parses_image_from_response(nano_banana):
    """Nano Banana 이미지 보강(reinforce) 응답을 PIL 이미지로 파싱한다."""
    nano_banana._llm.ainvoke = AsyncMock(return_value=_make_image_response())

    result = await nano_banana.reinforce_image(
        "make it more vibrant", _make_previous_image()
    )

    assert isinstance(result, PILModule.Image)


async def test_nano_banana_reinforce_image_raises_for_unsupported_format(nano_banana):
    """지원하지 않는 포맷의 원본 이미지로 보강을 요청하면 예외가 발생한다."""
    with pytest.raises(ValueError, match="Unsupported image format"):
        await nano_banana.reinforce_image(
            "make it more vibrant", _make_previous_image(fmt="WEBP")
        )


async def test_gpt_image2_create_image_parses_image_from_response(gpt_image2):
    """GPT-Image-2 응답의 base64 이미지를 PIL 이미지로 파싱한다."""
    gpt_image2._llm.async_client.images.generate = AsyncMock(
        return_value=_make_images_response(_make_image_base64())
    )

    result = await gpt_image2.create_image("a cat sitting on a couch")

    assert isinstance(result, PILModule.Image)


async def test_gpt_image2_reinforce_image_parses_image_from_response(gpt_image2):
    """GPT-Image-2 이미지 보강 응답을 PIL 이미지로 파싱한다."""
    gpt_image2._llm.async_client.images.edit = AsyncMock(
        return_value=_make_images_response(_make_image_base64())
    )

    result = await gpt_image2.reinforce_image(
        "make it more vibrant", _make_previous_image()
    )

    assert isinstance(result, PILModule.Image)


async def test_gpt_image2_reinforce_image_raises_for_unsupported_format(gpt_image2):
    """지원하지 않는 포맷의 원본 이미지로 보강을 요청하면 예외가 발생한다."""
    with pytest.raises(ValueError, match="Unsupported image format"):
        await gpt_image2.reinforce_image(
            "make it more vibrant", _make_previous_image(fmt="WEBP")
        )


async def test_gpt_image2_create_image_raises_when_no_image_data(gpt_image2):
    """응답에 이미지 데이터가 없으면 예외가 발생한다."""
    gpt_image2._llm.async_client.images.generate = AsyncMock(
        return_value=_make_images_response(None)
    )

    with pytest.raises(ValueError, match="No image data received"):
        await gpt_image2.create_image("a cat sitting on a couch")
