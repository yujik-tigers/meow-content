import base64

import requests

from app.settings import app_config


class ImageCreator:
    """A class to create images based on quotes using an LLM."""

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
            # "width": 1024,
            # "height": 1024,
            "wdith": 512,
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


image_creator = ImageCreator()
