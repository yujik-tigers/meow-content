import pytest

from app.enums import ContentType, GptImageModel, NanoBananaModel
from app.image_generator.daily_quote_image_generator import DailyQuoteImageGenerator
from app.image_generator.diffusion_model import GptImage2, NanoBanana
from app.image_generator.factory import ImageGeneratorFactory
from app.image_generator.literal_quote_image_generator import (
    LiteralQuoteImageGenerator,
)


@pytest.fixture(autouse=True)
def mock_clients(mocker):
    mocker.patch("app.image_generator.diffusion_model.ChatGoogleGenerativeAI")
    mocker.patch("app.image_generator.diffusion_model.AsyncOpenAI")
    mocker.patch("app.image_generator.factory.LocalImageStorage")


def test_get_image_generator_with_nano_banana_model():
    """Nano Banana 모델 요청 시 NanoBanana 기반 생성기를 반환한다."""
    generator = ImageGeneratorFactory.get_image_generator(
        ContentType.QUOTE, NanoBananaModel.NANO_BANANA_2
    )

    assert isinstance(generator, DailyQuoteImageGenerator)
    assert isinstance(generator._model, NanoBanana)


def test_get_image_generator_with_gpt_image_model():
    """GPT-Image 모델 요청 시 GptImage2 기반 생성기를 반환한다."""
    generator = ImageGeneratorFactory.get_image_generator(
        ContentType.QUOTE, GptImageModel.GPT_IMAGE_2
    )

    assert isinstance(generator, DailyQuoteImageGenerator)
    assert isinstance(generator._model, GptImage2)


def test_get_image_generator_for_literal_quote():
    """literal_quote 타입 요청 시 LiteralQuoteImageGenerator를 반환한다."""
    generator = ImageGeneratorFactory.get_image_generator(
        ContentType.LiteralQuote, GptImageModel.GPT_IMAGE_2
    )

    assert isinstance(generator, LiteralQuoteImageGenerator)


def test_get_image_generator_raises_for_unsupported_content_type():
    """이미지 생성을 지원하지 않는 콘텐츠 타입이면 예외가 발생한다."""
    with pytest.raises(ValueError, match="Unsupported content type"):
        ImageGeneratorFactory.get_image_generator(
            ContentType.REDDIT_MEME, GptImageModel.GPT_IMAGE_2
        )
