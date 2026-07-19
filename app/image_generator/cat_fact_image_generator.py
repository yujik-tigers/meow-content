from dataclasses import replace
from datetime import date, datetime
from typing import override

from app.enums import ContentStatus, RegenerateType
from app.image_generator import image_text_renderer
from app.image_generator.base import ImageGenerator
from app.image_generator.diffusion_model import DiffusionModel
from app.image_generator.image_storage import ImageStorage
from app.schema.content import Content


class CatFactImageGenerator(ImageGenerator):

    def __init__(self, model: DiffusionModel, image_storage: ImageStorage) -> None:
        self._model = model
        self._image_storage = image_storage

    @override
    async def generate(self, content: Content) -> Content:
        prompt = f"""Create an image of a cat that captures the mood and essence of this fun cat fact:

"{content.content}"

Interpret the fact freely — choose whatever art style, setting, lighting, and composition best brings it to life.
It can be a photograph, painting, illustration, or any other style that feels right.
The cat's pose, expression, and surroundings should feel connected to the fact.
No text in the image."""
        image = await self._model.create_image(
            prompt,
        )

        assert content.content is not None, "Content text must not be None"

        text_rendered_image = image_text_renderer.add_text(image, content.content)

        image_url = await self._image_storage.upload_image(
            text_rendered_image, f"fact/{date.today()}/{content.id}.png"
        )

        return replace(
            content,
            image_url=image_url,
            status=ContentStatus.PENDING,
        )

    @override
    async def regenerate(
        self, content: Content, prompt: str, regenerate_type: RegenerateType
    ) -> Content:
        if regenerate_type == RegenerateType.NEW:
            image_generate_prompt = f"""
Create an image of a cat based on this cat fact and user feedback.
Return only the edited image.

# Fact
{content.content}

# User Feedback
{prompt}
"""
            new_image = await self._model.create_image(image_generate_prompt)
        else:
            assert (
                content.image_url is not None
            ), "Content must have an existing image URL for regeneration"
            image = await self._image_storage.download_image(content.image_url)
            image_generate_prompt = f"""
You are an image editing assistant.
The user will provide an existing image and a description of the changes they want.
Edit the image according to the instructions while preserving its overall composition and style.
Return only the edited image.

# User Feedback
{prompt}
    """
            new_image = await self._model.reinforce_image(image_generate_prompt, image)

        assert content.content is not None, "Content text must not be None"

        text_rendered_image = image_text_renderer.add_text(new_image, content.content)

        timestamp = datetime.now().strftime("%y%m%d%H%M%S")
        image_url = await self._image_storage.upload_image(
            text_rendered_image,
            f"fact/{date.today()}/{content.id}/edited/{timestamp}.png",
        )

        return replace(
            content,
            image_url=image_url,
            status=ContentStatus.PENDING,
        )
