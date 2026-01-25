import os
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse

from app.contents.image_creator import ImageCreator
from app.dependencies import inject_daily_quote, inject_image_creator

router = APIRouter(prefix="/contents", tags=["contents"])


@router.post("/")
async def create_content(
    image_creator: Annotated[ImageCreator, Depends(inject_image_creator)],
    daily_quote: Annotated[str, Depends(inject_daily_quote)],
    date: date,
) -> FileResponse:
    """
    Create content for the given date with specified width and height.
    """
    file_path = f"{os.getcwd()}/app/images/{date.strftime('%Y%m%d')}.png"
    image_bytes = await image_creator.create_image(quote=daily_quote)
    with open(file_path, "wb") as f:
        f.write(image_bytes)
    return FileResponse(
        path=file_path,
        media_type="image/png",
    )
