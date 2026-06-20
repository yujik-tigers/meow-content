import pytest

from app.enums import ContentType, GptImageModel, NanoBananaModel
from app.image_generator.daily_quote_image_generator import DailyQuoteImageGenerator
from app.image_generator.diffusion_model import GptImage2, NanoBanana
from app.image_generator.factory import ImageGeneratorFactory


@pytest.fixture(autouse=True)
def mock_clients(mocker):
    mocker.patch("app.image_generator.diffusion_model.ChatGoogleGenerativeAI")
    mocker.patch("app.image_generator.diffusion_model.ChatOpenAI")
    mocker.patch("app.image_generator.factory.S3Client")


def test_get_image_generator_with_nano_banana_model():
    generator = ImageGeneratorFactory.get_image_generator(
        ContentType.QUOTE, NanoBananaModel.NANO_BANANA_2
    )

    assert isinstance(generator, DailyQuoteImageGenerator)
    assert isinstance(generator._model, NanoBanana)


def test_get_image_generator_with_gpt_image_model():
    generator = ImageGeneratorFactory.get_image_generator(
        ContentType.QUOTE, GptImageModel.GPT_IMAGE_2
    )

    assert isinstance(generator, DailyQuoteImageGenerator)
    assert isinstance(generator._model, GptImage2)


def test_get_image_generator_raises_for_unsupported_content_type():
    with pytest.raises(ValueError, match="Unsupported content type"):
        ImageGeneratorFactory.get_image_generator(
            ContentType.REDDIT_MEME, GptImageModel.GPT_IMAGE_2
        )
