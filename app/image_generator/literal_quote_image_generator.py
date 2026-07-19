from dataclasses import replace
from datetime import date
from typing import override

from app.enums import ContentStatus
from app.image_generator import image_text_renderer
from app.image_generator.base import ImageGenerator
from app.image_generator.diffusion_model import DiffusionModel
from app.image_generator.image_storage import ImageStorage
from app.schema.content import Content


class LiteralQuoteImageGenerator(ImageGenerator):

    def __init__(self, model: DiffusionModel, image_storage: ImageStorage) -> None:
        self._model = model
        self._image_storage = image_storage

    @override
    async def generate(self, content: Content) -> Content:
        prompt = f"""Create an image of a cat that captures the mood and essence of this movie quote:

"{content.content}"

This line is from the movie "{content.title}". Interpret the quote and its cinematic mood freely — choose whatever art style, setting, lighting, and composition best brings it to life.
It can be a photograph, painting, illustration, or any other style that feels right.
The cat's pose, expression, and surroundings should feel emotionally connected to the quote and its scene.
No text in the image."""
        image = await self._model.create_image(
            prompt,
        )

        assert (
            content.content is not None
            and content.author is not None
            and content.title is not None
        ), "Content text, author, and title must not be None"

        text_rendered_image = image_text_renderer.add_text(
            image, content.content, f"{content.author}, {content.title}"
        )

        image_url = await self._image_storage.upload_image(
            text_rendered_image, f"literal_quote/{date.today()}/{content.id}.png"
        )

        return replace(
            content,
            image_url=image_url,
            status=ContentStatus.PENDING,
        )
