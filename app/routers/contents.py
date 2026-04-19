import io
import os
import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Response

from app.contents import image_retriever
from app.contents.enums import ImageType, LanguageCode
from app.contents.quote_image_creator import QuoteImageCreator
from app.dependencies import (
    inject_quote_image_creator,
)
from app.schemas.contents import CreateContentRequest

router = APIRouter(prefix="/contents", tags=["contents"])


@router.post(
    "/quotes",
    response_class=Response,
    responses={
        200: {
            "content": {
                "multipart/mixed": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "base": {
                                "type": "string",
                                "format": "binary",
                                "description": "Raw cat image",
                            },
                            "english": {
                                "type": "string",
                                "format": "binary",
                                "description": "English quote image",
                            },
                            "korean": {
                                "type": "string",
                                "format": "binary",
                                "description": "Korean quote image",
                            },
                        },
                    },
                }
            }
        }
    },
)
async def create_content(
    quote_image_creator: Annotated[
        QuoteImageCreator, Depends(inject_quote_image_creator)
    ],
    request: CreateContentRequest,
) -> Response:
    """
    Create content for the given date.
    """
    image_paths = await quote_image_creator.create(date=request.created_at)

    parts = [
        ("base", image_paths.base_image_path, "image/png"),
        ("english", image_paths.quote_image_path, "image/png"),
        ("korean", image_paths.korean_quote_image_path, "image/png"),
    ]

    boundary = uuid.uuid4().hex
    body = generate_multipart(boundary, parts)

    return Response(
        content=body,
        media_type=f"multipart/mixed; boundary={boundary}",
    )


# @router.post(
#     "/korean_memes",
#     response_class=FileResponse,
#     responses={200: {"content": {"image/jpeg": {}}}},
# )
# async def create_korean_meme(
#     content_creator: Annotated[ContentCreator, Depends(inject_quote_image_creator)],
#     request: CreateKoreanMemeRequest,
# ) -> FileResponse:
#     """
#     Create korean meme for the given date.
#     """

#     if image_retriever.is_exist(LanguageCode.KOREAN, request.created_at):
#         return FileResponse(
#             path=image_retriever.get_image_path(
#                 LanguageCode.KOREAN, request.created_at
#             ),
#             media_type="image/jpeg",
#         )

#     # Image Description

#     # Vector DB search for meme keyword

#     # Generate meme text with keyword based on the image and image description

#     # Generate meme image with meme text

#     # Evaluate the generated meme image

#     content_file_path = await content_creator.create_meme(
#         language_code=request.language, date=request.created_at
#     )

#     return FileResponse(
#         path=content_file_path,
#         media_type="image/png",
#     )


@router.delete(
    "/{date}/{language_code}/{ImageType}",
    status_code=204,
)
async def delete_content(
    date: datetime,
    language_code: LanguageCode,
) -> None:
    """
    Delete content for the given date and language code.
    """
    file_path = image_retriever.get_image_path(
        language_code=language_code, date=date, image_type=ImageType.QUOTE
    )
    if image_retriever.is_exist(
        language_code=language_code, date=date, image_type=ImageType.QUOTE
    ):
        os.remove(file_path)


def generate_multipart(boundary: str, parts: list[tuple[str, str, str]]) -> bytes:
    buf = io.BytesIO()
    for name, path, media_type in parts:
        filename = os.path.basename(path)
        with open(path, "rb") as f:
            data = f.read()
        buf.write(f"--{boundary}\r\n".encode())
        buf.write(
            f'Content-Disposition: attachment; name="{name}"; filename="{filename}"\r\n'.encode()
        )
        buf.write(f"Content-Type: {media_type}\r\n\r\n".encode())
        buf.write(data)
        buf.write(b"\r\n")
    buf.write(f"--{boundary}--\r\n".encode())
    return buf.getvalue()
