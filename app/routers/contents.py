import os
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse

from app.contents.image_creator import ImageCreator
from app.dependencies import inject_image_creator

router = APIRouter(prefix="/contents", tags=["contents"])


@router.post("/")
async def create_content(
    image_creator: Annotated[ImageCreator, Depends(inject_image_creator)],
    date: date,
    width: int = 800,
    height: int = 600,
) -> FileResponse:
    """
    Create content for the given date with specified width and height.
    """
    file_path = (
        f"{os.getcwd()}/app/images/{date.strftime('%Y%m%d')}_{width}x{height}.png"
    )
    image_bytes = await image_creator.create_image(
        width=width, height=height, quote="Cats are great companions."
    )
    with open(file_path, "wb") as f:
        f.write(image_bytes)
    return FileResponse(
        path=file_path,
        media_type="image/png",
    )
