from datetime import date

from google.genai import Client, types

from app.contents import (
    image_retriever,
    image_text_renderer,
    quote_translator,
)
from app.contents.enums import ImageType, LanguageCode
from app.contents.quote_creator import Quote, create_daily_quote
from app.schemas.contents import QuoteImagePaths


class QuoteImageCreator:
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

    async def create(self, date: date) -> QuoteImagePaths:
        if image_retriever.is_exist(LanguageCode.NONE, date, ImageType.QUOTE):
            return QuoteImagePaths(
                base_image_path=image_retriever.get_image_path(
                    LanguageCode.NONE, date, ImageType.QUOTE
                ),
                quote_image_path=image_retriever.get_image_path(
                    LanguageCode.ENGLISH, date, ImageType.QUOTE
                ),
                korean_quote_image_path=image_retriever.get_image_path(
                    LanguageCode.KOREAN, date, ImageType.QUOTE
                ),
            )

        quote = await create_daily_quote()
        korean_quote = await quote_translator.translate(quote.text, LanguageCode.KOREAN)

        client = Client()
        prompt = self.quote_generate_prompt.format(quote=quote)

        response = await client.aio.models.generate_content(
            model="gemini-3-pro-image-preview",
            contents=[prompt],
            config=types.GenerateContentConfig(
                image_config=types.ImageConfig(aspect_ratio="1:1", image_size="1K"),
            ),
        )
        base_image = self._parse_image_response(response)
        await self._save_image(
            image_bytes=base_image,
            language_code=LanguageCode.NONE,
            date=date,
            image_type=ImageType.QUOTE,
        )

        await self._save_image(
            image_bytes=image_text_renderer.add_quote(
                image_bytes=base_image, quote=quote
            ),
            language_code=LanguageCode.ENGLISH,
            date=date,
            image_type=ImageType.QUOTE,
        )
        await self._save_image(
            image_bytes=image_text_renderer.add_quote(
                image_bytes=base_image,
                quote=Quote(text=korean_quote, speaker=quote.speaker),
            ),
            language_code=LanguageCode.KOREAN,
            date=date,
            image_type=ImageType.QUOTE,
        )
        return QuoteImagePaths(
            base_image_path=image_retriever.get_image_path(
                LanguageCode.NONE, date, ImageType.QUOTE
            ),
            quote_image_path=image_retriever.get_image_path(
                LanguageCode.ENGLISH, date, ImageType.QUOTE
            ),
            korean_quote_image_path=image_retriever.get_image_path(
                LanguageCode.KOREAN, date, ImageType.QUOTE
            ),
        )

    def _parse_image_response(self, response: types.GenerateContentResponse) -> bytes:
        if response.parts is not None:
            for part in response.parts:
                if part.inline_data is not None:
                    image_bytes = part.inline_data.data
                    if image_bytes is not None:
                        return image_bytes

        raise ValueError("No image data found in the response.")

    async def _save_image(
        self,
        image_bytes: bytes,
        language_code: LanguageCode,
        date: date,
        image_type: ImageType,
    ) -> None:
        file_path = image_retriever.get_image_path(
            language_code=language_code, date=date, image_type=image_type
        )
        with open(file_path, "wb") as f:
            f.write(image_bytes)


quote_image_creator = QuoteImageCreator()
