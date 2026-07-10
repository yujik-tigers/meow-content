import httpx

from app.enums import ContentType
from app.schema.content import NewContent


async def fetch_daily_quotes() -> list[NewContent]:
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get("https://zenquotes.io/api/quotes")
    response.raise_for_status()
    return [
        NewContent(type=ContentType.QUOTE, content=quote["q"], author=quote["a"])
        for quote in response.json()
    ]
