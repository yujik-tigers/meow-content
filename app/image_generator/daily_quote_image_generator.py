from dataclasses import replace
from datetime import date, datetime
from typing import override

from app.enums import ContentStatus, NanoBananaModel
from app.image_generator import image_text_renderer
from app.image_generator.base import ImageGenerator
from app.image_generator.diffusion_model import DiffusionModel, NanoBanana
from app.image_generator.s3_uploader import S3Client
from app.schema.content import Content


class DailyQuoteImageGenerator(ImageGenerator):

    def __init__(self, model: DiffusionModel, s3_client: S3Client) -> None:
        self._model = model
        self._s3_client = s3_client

    @override
    async def generate(self, content: Content) -> Content:
        prompt = f"""Create an image of a cat that captures the mood and essence of this quote:

"{content.content}"

Interpret the quote freely — choose whatever art style, setting, lighting, and composition best brings it to life.
It can be a photograph, painting, illustration, or any other style that feels right.
The cat's pose, expression, and surroundings should feel emotionally connected to the quote.
No text in the image."""
        image = await self._model.create_image(
            prompt,
        )

        assert (
            content.content is not None and content.author is not None
        ), "Content text and author must not be None"

        text_rendered_image = image_text_renderer.add_text(
            image, content.content, content.author
        )

        image_url = await self._s3_client.upload_image(
            text_rendered_image, f"daily_quote/{date.today()}/{content.id}.png"
        )

        return replace(
            content,
            image_url=image_url,
            status=ContentStatus.PENDING,
        )

    @override
    async def regenerate(self, content: Content, prompt: str) -> Content:
        assert (
            content.image_url is not None
        ), "Content must have an existing image URL for regeneration"
        image = await self._s3_client.download_image(content.image_url)
        new_image = await self._model.recreate_image(image, prompt)

        assert (
            content.content is not None and content.author is not None
        ), "Content text and author must not be None"

        text_rendered_image = image_text_renderer.add_text(
            new_image, content.content, content.author
        )

        timestamp = datetime.now().strftime("%y%m%d%H%M%S")
        image_url = await self._s3_client.upload_image(
            text_rendered_image,
            f"daily_quote/{date.today()}/{content.id}/edited/{timestamp}.png",
        )

        return replace(
            content,
            image_url=image_url,
            status=ContentStatus.PENDING,
        )


daily_quote_image_generator = DailyQuoteImageGenerator(
    NanoBanana(NanoBananaModel.NANO_BANANA_2), S3Client()
)
