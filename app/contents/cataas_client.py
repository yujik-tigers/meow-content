# CATAAS
# Cat as a Service API Client
# https://cataas.com/#/


import httpx


async def get_daily_cat_image() -> bytes:
    async with httpx.AsyncClient() as client:
        response = await client.get("https://cataas.com/cat")
    response.raise_for_status()
    return response.content
