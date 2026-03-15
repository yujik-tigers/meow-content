from abc import ABC, abstractmethod
from datetime import date
from typing import override

from google.genai import Client, types

from app.contents import (
    cataas_client,
    image_retriever,
    image_text_renderer,
    meme_text_generator,
    quote_translator,
)
from app.contents.enums import LanguageCode
from app.contents.quote_creator import Quote


class ContentCreator(ABC):
    """A class to create content based on quotes using an LLM."""

    def __init__(self):
        self.quote_generate_prompt = """
Please create a cat image that matches the mood and theme of the given quote.
Do not include any text in the image.

# Quote:
{quote}
"""
        self.meme_generate_prompt = """
Put the given text into speech bubbles in the given image.
        """

    @abstractmethod
    async def create_quote_image(
        self, quote: Quote, language_code: LanguageCode, date: date
    ) -> str:
        """
        Create content based on the given quote, language code, and date.
        Return the file path of the created content.
        """
        pass

    @abstractmethod
    async def create_meme(self, language_code: LanguageCode, date: date) -> str:
        """
        Create meme content.
        Return the file path of the created meme content.
        """
        pass


# class CloudflareContentCreator(ContentCreator):

#     @override
#     async def create(self, quote: str, language_code: LanguageCode) -> str:

#         url = f"https://api.cloudflare.com/client/v4/accounts/{app_config.CLOUDFLARE_ACCOUNT_ID}/ai/run/{app_config.CLOUDFLARE_IMAGE_GEN_MODEL}"
#         headers = {
#             "Authorization": f"Bearer {app_config.CLOUDFLARE_API_KEY}",
#         }
#         form = {
#             "prompt": self.prompt.format(quote=quote),
#             "steps": 20,
#             "width": 512,
#             "height": 512,
#         }

#         response = requests.post(
#             url,
#             headers=headers,
#             data=form,
#         )
#         response.raise_for_status()

#         result = response.json()

#         base_64 = result.get("result", {}).get("image")
#         try:
#             image_bytes = base64.b64decode(base_64)
#         except Exception as e:
#             print(f"Error decoding base64 image: {e}")
#             raise

#         return image_bytes


class GeminiContentCreator(ContentCreator):

    @override
    async def create_quote_image(
        self, quote: Quote, language_code: LanguageCode, date: date
    ) -> str:
        if language_code != LanguageCode.ENGLISH:
            quote.text = await quote_translator.translate(
                quote_text=quote.text, target_language_code=language_code
            )

        client = Client()
        prompt = self.quote_generate_prompt.format(quote=quote)

        if not image_retriever.is_exist(LanguageCode.NONE, date):
            response = client.models.generate_content(
                model="gemini-3-pro-image-preview",
                contents=[prompt],
                config=types.GenerateContentConfig(
                    image_config=types.ImageConfig(aspect_ratio="1:1", image_size="1K"),
                ),
            )
            base_image = self._parse_image_response(response)
            await self._save_image(
                image_bytes=base_image, language_code=LanguageCode.NONE, date=date
            )

        if language_code == LanguageCode.NONE:
            return image_retriever.get_image_path(LanguageCode.NONE, date)

        base_image = image_retriever.retrieve(LanguageCode.NONE, date)
        await self._save_image(
            image_bytes=image_text_renderer.add_quote(
                image_bytes=base_image, quote=quote
            ),
            language_code=language_code,
            date=date,
        )
        return image_retriever.get_image_path(language_code, date)

    @override
    async def create_meme(self, language_code: LanguageCode, date: date) -> str:
        client = Client()

        if not image_retriever.is_exist(LanguageCode.NONE, date):
            base_image = await cataas_client.get_daily_cat_image()
            await self._save_image(
                image_bytes=base_image, language_code=LanguageCode.NONE, date=date
            )

        if language_code == LanguageCode.NONE:
            return image_retriever.get_image_path(LanguageCode.NONE, date)

        meme_text = await meme_text_generator.generate_speech_bubble_text(
            image_bytes=image_retriever.retrieve(LanguageCode.NONE, date),
            language_code=language_code,
        )

        base_image = image_retriever.retrieve(LanguageCode.NONE, date)
        response = client.models.generate_content(
            model="gemini-3-pro-image-preview",
            contents=[
                self.meme_generate_prompt,
                "# Image:",
                types.Part.from_bytes(data=base_image, mime_type="image/jpeg"),
                "# Text:",
                meme_text,
            ],
            config=types.GenerateContentConfig(
                response_modalities=["text", "image"],
            ),
        )
        meme_image = self._parse_image_response(response=response)
        await self._save_image(
            image_bytes=meme_image, language_code=language_code, date=date
        )
        return image_retriever.get_image_path(language_code, date)

    def _parse_image_response(self, response: types.GenerateContentResponse) -> bytes:
        if response.parts is not None:
            for part in response.parts:
                if part.inline_data is not None:
                    image_bytes = part.inline_data.data
                    if image_bytes is not None:
                        return image_bytes

        raise ValueError("No image data found in the response.")

    async def _save_image(
        self, image_bytes: bytes, language_code: LanguageCode, date: date
    ) -> None:
        file_path = image_retriever.get_image_path(
            language_code=language_code, date=date
        )
        with open(file_path, "wb") as f:
            f.write(image_bytes)


content_creator = GeminiContentCreator()
