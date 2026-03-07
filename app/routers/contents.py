from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse

from app.contents import image_retriever
from app.contents.image_creator import ContentCreator
from app.contents.quote_creator import Quote
from app.dependencies import (
    inject_content_creator,
    inject_quote,
)
from app.schemas.contents import CreateContentRequest

router = APIRouter(prefix="/contents", tags=["contents"])


@router.post(
    "", response_class=FileResponse, responses={200: {"content": {"image/png": {}}}}
)
async def create_content(
    content_creator: Annotated[ContentCreator, Depends(inject_content_creator)],
    daily_quote: Annotated[Quote, Depends(inject_quote)],
    request: CreateContentRequest,
) -> FileResponse:
    """
    Create content for the given date.
    """
    if image_retriever.is_exist(request.language, request.created_at):
        return FileResponse(
            path=image_retriever.get_image_path(request.language, request.created_at),
            media_type="image/png",
        )

    content_file_path = await content_creator.create(
        quote=daily_quote, language_code=request.language, date=request.created_at
    )

    return FileResponse(
        path=content_file_path,
        media_type="image/png",
    )
