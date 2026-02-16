from app.contents.image_creator import ImageCreator, image_creator
from app.contents.quote_creator import quote_creator
from app.contents.quote_translator import QuoteTranslator, quote_translator


async def inject_image_creator() -> ImageCreator:
    return image_creator


async def inject_daily_quote() -> str:
    return await quote_creator.create_daily_quote()


async def inject_quote_translator() -> QuoteTranslator:
    return quote_translator
