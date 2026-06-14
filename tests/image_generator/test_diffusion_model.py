from unittest.mock import MagicMock

import pytest
from PIL import Image as PILModule

from app.enums import NanoBananaModel
from app.image_generator.diffusion_model import NanoBanana


@pytest.fixture
def nano_banana(mocker):
    mocker.patch("app.image_generator.diffusion_model.genai.Client")
    return NanoBanana(NanoBananaModel.NANO_BANANA_2)


def _make_image_response() -> MagicMock:
    inner = MagicMock()
    inner._pil_image = PILModule.new("RGB", (10, 10), "blue")

    part = MagicMock()
    part.text = None
    part.inline_data = MagicMock()
    part.as_image.return_value = inner

    response = MagicMock()
    response.parts = [part]
    return response


async def test_create_image_parses_image_from_response(nano_banana):
    nano_banana._client.models.generate_content.return_value = _make_image_response()

    result = await nano_banana.create_image("a cat sitting on a couch")

    assert isinstance(result, PILModule.Image)


async def test_recreate_image_parses_image_from_response(nano_banana):
    nano_banana._client.models.generate_content.return_value = _make_image_response()

    result = await nano_banana.reinforce_image(
        "make it more vibrant",
        PILModule.new("RGB", (10, 10), "red"),
    )

    assert isinstance(result, PILModule.Image)
