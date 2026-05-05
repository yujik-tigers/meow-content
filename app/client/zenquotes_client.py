import httpx

from app.schema.contents import Quote


async def create_daily_quote() -> Quote:
    async with httpx.AsyncClient() as client:
        response = await client.get("https://zenquotes.io/api/today")
    response.raise_for_status()
    response_json = response.json()
    return Quote(
        text=response_json[0]["q"],
        speaker=response_json[0]["a"],
    )
