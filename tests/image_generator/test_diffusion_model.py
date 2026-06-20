import base64
from io import BytesIO
from unittest.mock import AsyncMock

import pytest
from langchain.messages import AIMessage
from PIL import Image as PILModule

from app.enums import NanoBananaModel
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


def _make_empty_response() -> AIMessage:
    return AIMessage(
        content=[{"type": "text", "text": "no image here"}],
        response_metadata={"output_version": "v1"},
    )


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
    mocker.patch("app.image_generator.diffusion_model.ChatOpenAI")
    return GptImage2()


async def test_nano_banana_create_image_parses_image_from_response(nano_banana):
    nano_banana._llm.ainvoke = AsyncMock(return_value=_make_image_response())

    result = await nano_banana.create_image("a cat sitting on a couch")

    assert isinstance(result, PILModule.Image)


async def test_nano_banana_reinforce_image_parses_image_from_response(nano_banana):
    nano_banana._llm.ainvoke = AsyncMock(return_value=_make_image_response())

    result = await nano_banana.reinforce_image(
        "make it more vibrant", _make_previous_image()
    )

    assert isinstance(result, PILModule.Image)


async def test_nano_banana_reinforce_image_raises_for_unsupported_format(nano_banana):
    with pytest.raises(ValueError, match="Unsupported image format"):
        await nano_banana.reinforce_image(
            "make it more vibrant", _make_previous_image(fmt="WEBP")
        )


async def test_gpt_image2_create_image_parses_image_from_response(gpt_image2):
    gpt_image2._llm.ainvoke = AsyncMock(return_value=_make_image_response())

    result = await gpt_image2.create_image("a cat sitting on a couch")

    assert isinstance(result, PILModule.Image)


async def test_gpt_image2_reinforce_image_parses_image_from_response(gpt_image2):
    gpt_image2._llm.ainvoke = AsyncMock(return_value=_make_image_response())

    result = await gpt_image2.reinforce_image(
        "make it more vibrant", _make_previous_image()
    )

    assert isinstance(result, PILModule.Image)


async def test_gpt_image2_reinforce_image_raises_for_unsupported_format(gpt_image2):
    with pytest.raises(ValueError, match="Unsupported image format"):
        await gpt_image2.reinforce_image(
            "make it more vibrant", _make_previous_image(fmt="WEBP")
        )


async def test_parse_image_from_response_raises_when_no_image_block(gpt_image2):
    gpt_image2._llm.ainvoke = AsyncMock(return_value=_make_empty_response())

    with pytest.raises(ValueError, match="No image data received"):
        await gpt_image2.create_image("a cat sitting on a couch")
