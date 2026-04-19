from app.contents.quote_image_creator import QuoteImageCreator, quote_image_creator


async def inject_quote_image_creator() -> QuoteImageCreator:
    return quote_image_creator
