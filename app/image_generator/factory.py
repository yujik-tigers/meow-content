from app.enums import ContentType, GptImageModel, NanoBananaModel
from app.image_generator.base import ImageGenerator
from app.image_generator.daily_quote_image_generator import DailyQuoteImageGenerator
from app.image_generator.diffusion_model import GptImage2, NanoBanana
from app.image_generator.literal_quote_image_generator import (
    LiteralQuoteImageGenerator,
)
from app.image_generator.local_image_storage import LocalImageStorage


class ImageGeneratorFactory:
    @staticmethod
    def get_image_generator(
        content_type: ContentType, diffusion_model: NanoBananaModel | GptImageModel
    ) -> ImageGenerator:
        if isinstance(diffusion_model, NanoBananaModel):
            model = NanoBanana(diffusion_model)
        else:
            model = GptImage2(diffusion_model)

        if content_type == ContentType.QUOTE:
            return DailyQuoteImageGenerator(
                model=model, image_storage=LocalImageStorage()
            )
        if content_type == ContentType.LiteralQuote:
            return LiteralQuoteImageGenerator(
                model=model, image_storage=LocalImageStorage()
            )

        raise ValueError(f"Unsupported content type to generate image: {content_type}")
