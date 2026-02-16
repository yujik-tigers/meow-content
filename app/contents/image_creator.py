import base64
from abc import ABC, abstractmethod
from typing import override

import requests
from google.genai import Client, types

from app.settings import app_config


class ImageCreator(ABC):
    """A class to create images based on quotes using an LLM."""

    @abstractmethod
    async def create_image(self, quote: str) -> bytes:
        pass


class CloudflareImageCreator(ImageCreator):

    @override
    async def create_image(self, quote: str) -> bytes:
        prompt = f"""
Please create a cat image that matches the given quote.
Please include the quote naturally just once, like an internet meme.

# Quote:
{quote}
    """

        url = f"https://api.cloudflare.com/client/v4/accounts/{app_config.CLOUDFLARE_ACCOUNT_ID}/ai/run/{app_config.CLOUDFLARE_IMAGE_GEN_MODEL}"
        headers = {
            "Authorization": f"Bearer {app_config.CLOUDFLARE_API_KEY}",
        }
        form = {
            "prompt": prompt,
            "steps": 20,
            "width": 512,
            "height": 512,
        }

        response = requests.post(
            url,
            headers=headers,
            data=form,
        )
        response.raise_for_status()

        result = response.json()

        base_64 = result.get("result", {}).get("image")
        try:
            return base64.b64decode(base_64)
        except Exception as e:
            print(f"Error decoding base64 image: {e}")
            raise


class GeminiImageCreator(ImageCreator):

    @override
    async def create_image(self, quote: str) -> bytes:
        client = Client()
        prompt = f"""
Please create a cat image that matches the given quote.
Please include the quote naturally just once, like an internet meme.

# Quote:
{quote}
        """
        response = client.models.generate_content(
            model="gemini-3-pro-image-preview",
            contents=[prompt],
            config=types.GenerateContentConfig(
                image_config=types.ImageConfig(aspect_ratio="1:1", image_size="1K"),
            ),
        )

        if response.parts is not None:
            for part in response.parts:
                if part.inline_data is not None:
                    generate_image = part.inline_data.data
                    if generate_image is not None:
                        return generate_image

        raise ValueError("No image data found in the response.")


image_creator = GeminiImageCreator()
