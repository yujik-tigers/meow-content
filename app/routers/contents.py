import os
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse

from app.contents.enums import LanguageCode
from app.contents.image_creator import ImageCreator
from app.contents.quote_translator import QuoteTranslator
from app.dependencies import (
    inject_daily_quote,
    inject_image_creator,
    inject_quote_translator,
)
from app.schemas.contents import CreateContentRequest

router = APIRouter(prefix="/contents", tags=["contents"])


@router.post(
    "", response_class=FileResponse, responses={200: {"content": {"image/png": {}}}}
)
async def create_content(
    image_creator: Annotated[ImageCreator, Depends(inject_image_creator)],
    daily_quote: Annotated[str, Depends(inject_daily_quote)],
    quote_translator: Annotated[QuoteTranslator, Depends(inject_quote_translator)],
    request: CreateContentRequest,
) -> FileResponse:
    """
    Create content for the given date with specified width and height.
    """
    file_path = f"{os.getcwd()}/app/images/{request.created_at.strftime('%Y%m%d')}_{request.language.value}.png"
    if os.path.exists(file_path):
        return FileResponse(
            path=file_path,
            media_type="image/png",
        )

    if request.language != LanguageCode.ENGLISH:
        print("current_quote: ", daily_quote)
        daily_quote = await quote_translator.translate(
            quote=daily_quote, target_language_code=request.language
        )
        print("translated_quote: ", daily_quote)

    image_bytes = await image_creator.create_image(quote=daily_quote)
    with open(file_path, "wb") as f:
        f.write(image_bytes)
    return FileResponse(
        path=file_path,
        media_type="image/png",
    )
