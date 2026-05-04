# CATAAS
# Cat as a Service API Client
# https://cataas.com/#/


from datetime import date

import httpx

from app.contents import image_manager
from app.contents.enums import ImageType


async def get_daily_cat_image(date: date) -> bytes:
    if image_manager.is_exist(date=date, image_type=ImageType.MEME):
        base_image_path = image_manager.find_image_path_by(
            date=date, image_type=ImageType.MEME
        )
        with open(base_image_path, "rb") as f:
            return f.read()
    async with httpx.AsyncClient() as client:
        response = await client.get("https://cataas.com/cat")
    response.raise_for_status()
    image_manager.save_image(
        image_bytes=response.content,
        date=date,
        image_type=ImageType.MEME,
        image_extension=response.headers.get("Content-Type", "image/jpeg").split("/")[
            -1
        ],
    )
    return response.content
