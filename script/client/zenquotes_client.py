import httpx

from script.schema import DailyQuoteRaw


async def create_daily_quotes() -> list[DailyQuoteRaw]:
    async with httpx.AsyncClient() as client:
        response = await client.get("https://zenquotes.io/api/quotes")
    response.raise_for_status()
    response_json = response.json()
    return [
        DailyQuoteRaw(
            quote=quote["q"],
            author=quote["a"],
        )
        for quote in response_json
    ]
