from app.contents.meme_image_creator import MemeImageCreator, meme_image_creator
from app.contents.quote_image_creator import QuoteImageCreator, quote_image_creator


async def inject_quote_image_creator() -> QuoteImageCreator:
    return quote_image_creator


async def inject_meme_image_creator() -> MemeImageCreator:
    return meme_image_creator
