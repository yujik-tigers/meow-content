import os
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse

from app.contents.enums import LanguageCode
from app.contents.image_creator import ImageCreator
from app.contents.image_text_renderer import add_meme_text
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
        daily_quote = await quote_translator.translate(
            quote=daily_quote, target_language_code=request.language
        )

    base_file_path = (
        f"{os.getcwd()}/app/images/{request.created_at.strftime('%Y%m%d')}.png"
    )
    image_bytes_with_meme = await _put_meme_text(
        base_file_path=base_file_path,
        image_creator=image_creator,
        daily_quote=daily_quote,
    )
    with open(file_path, "wb") as f:
        f.write(image_bytes_with_meme)
    return FileResponse(
        path=file_path,
        media_type="image/png",
    )


async def _put_meme_text(
    base_file_path: str, image_creator: ImageCreator, daily_quote: str
) -> bytes:
    if not os.path.exists(base_file_path):
        image_bytes = await image_creator.create_image(quote=daily_quote)
        with open(base_file_path, "wb") as f:
            f.write(image_bytes)
    else:
        with open(base_file_path, "rb") as f:
            image_bytes = f.read()

    return add_meme_text(image_bytes=image_bytes, text=daily_quote)
