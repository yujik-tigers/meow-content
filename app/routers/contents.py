import datetime
import os
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse

from app.contents.image_creator import ImageCreator
from app.dependencies import inject_daily_quote, inject_image_creator
from app.schemas.contents import CreateContentRequest

router = APIRouter(prefix="/contents", tags=["contents"])


@router.post("", responses={200: {"content": {"image/png": {}}}})
async def create_content(
    image_creator: Annotated[ImageCreator, Depends(inject_image_creator)],
    daily_quote: Annotated[str, Depends(inject_daily_quote)],
    request: CreateContentRequest,
) -> FileResponse:
    """
    Create content for the given date with specified width and height.
    """
    file_path = f"{os.getcwd()}/app/images/{request.created_at.strftime('%Y%m%d')}.png"
    if os.path.exists(file_path):
        return FileResponse(
            path=file_path,
            media_type="image/png",
        )

    image_bytes = await image_creator.create_image(quote=daily_quote)
    with open(file_path, "wb") as f:
        f.write(image_bytes)
    return FileResponse(
        path=file_path,
        media_type="image/png",
    )


@router.get("/test")
async def route_path_test(date: datetime.date) -> dict:
    file_path = f"{os.getcwd()}/app/images/{date.strftime('%Y%m%d')}.png"
    return {"file_path": file_path, "exists": os.path.exists(file_path)}
