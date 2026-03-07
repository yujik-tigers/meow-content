from app.contents.image_creator import ContentCreator, content_creator
from app.contents.quote_creator import Quote, create_daily_quote


async def inject_content_creator() -> ContentCreator:
    return content_creator


async def inject_quote() -> Quote:
    return await create_daily_quote()
