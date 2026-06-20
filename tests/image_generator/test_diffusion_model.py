import base64
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain.messages import AIMessage, HumanMessage
from PIL import Image as PILModule

from app.enums import GptImageModel, NanoBananaModel
from app.image_generator.diffusion_model import GptImage2, NanoBanana, _GptImage2ChatModel


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


@pytest.fixture
def gpt_image2_chat_model(mocker) -> _GptImage2ChatModel:
    mocker.patch("app.image_generator.diffusion_model.AsyncOpenAI")
    return _GptImage2ChatModel(model=GptImageModel.GPT_IMAGE_2.value)


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
    gpt_image2._llm.async_client.images.generate = AsyncMock(
        return_value=_make_images_response(_make_image_base64())
    )

    result = await gpt_image2.create_image("a cat sitting on a couch")

    assert isinstance(result, PILModule.Image)


async def test_gpt_image2_reinforce_image_parses_image_from_response(gpt_image2):
    gpt_image2._llm.async_client.images.edit = AsyncMock(
        return_value=_make_images_response(_make_image_base64())
    )

    result = await gpt_image2.reinforce_image(
        "make it more vibrant", _make_previous_image()
    )

    assert isinstance(result, PILModule.Image)


async def test_gpt_image2_reinforce_image_raises_for_unsupported_format(gpt_image2):
    with pytest.raises(ValueError, match="Unsupported image format"):
        await gpt_image2.reinforce_image(
            "make it more vibrant", _make_previous_image(fmt="WEBP")
        )


async def test_gpt_image2_create_image_raises_when_no_image_data(gpt_image2):
    gpt_image2._llm.async_client.images.generate = AsyncMock(
        return_value=_make_images_response(None)
    )

    with pytest.raises(ValueError, match="No image data received"):
        await gpt_image2.create_image("a cat sitting on a couch")


def test_extract_prompt_and_image_from_plain_string(gpt_image2_chat_model):
    prompt, image = gpt_image2_chat_model._extract_prompt_and_image(
        [HumanMessage("a cat sitting on a couch")]
    )

    assert prompt == "a cat sitting on a couch"
    assert image is None


def test_extract_prompt_and_image_from_content_blocks(gpt_image2_chat_model):
    image_base64 = _make_image_base64()

    prompt, image = gpt_image2_chat_model._extract_prompt_and_image(
        [
            HumanMessage(
                content=[
                    {"type": "text", "text": "make it more vibrant"},
                    {
                        "type": "image",
                        "base64": image_base64,
                        "mime_type": "image/png",
                    },
                ]
            )
        ]
    )

    assert prompt == "make it more vibrant"
    assert image == (image_base64, "image/png")


def test_image_to_file_decodes_base64(gpt_image2_chat_model):
    image_base64 = _make_image_base64()

    filename, buffer, mime = gpt_image2_chat_model._image_to_file(
        image_base64, "image/png"
    )

    assert filename == "image"
    assert mime == "image/png"
    assert buffer.getvalue() == base64.b64decode(image_base64)


def test_images_response_to_ai_message_raises_when_no_image_data(gpt_image2_chat_model):
    with pytest.raises(ValueError, match="No image data received"):
        gpt_image2_chat_model._images_response_to_ai_message(
            _make_images_response(None)
        )


def test_images_response_to_ai_message_sets_usage_metadata(gpt_image2_chat_model):
    usage = MagicMock(input_tokens=10, output_tokens=20, total_tokens=30)

    message = gpt_image2_chat_model._images_response_to_ai_message(
        _make_images_response(_make_image_base64(), usage=usage)
    )

    assert message.usage_metadata == {
        "input_tokens": 10,
        "output_tokens": 20,
        "total_tokens": 30,
    }


def test_images_response_to_ai_message_omits_usage_metadata_when_absent(
    gpt_image2_chat_model,
):
    message = gpt_image2_chat_model._images_response_to_ai_message(
        _make_images_response(_make_image_base64())
    )

    assert message.usage_metadata is None
