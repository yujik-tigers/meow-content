import io
import os
import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Response
from fastapi.responses import FileResponse
from starlette import status

from app.contents import image_manager, meme_analyzer
from app.contents.enums import ImageType, LanguageCode
from app.contents.meme_image_creator import MemeImageCreator
from app.contents.quote_image_creator import QuoteImageCreator
from app.db.repository import MemeRepository
from app.dependencies import (
    inject_meme_image_creator,
    inject_meme_repository,
    inject_quote_image_creator,
)
from app.schemas.common import ApiResponse
from app.schemas.contents import CreateContentRequest, MemeCandidate

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


@router.post(
    "/korean_memes",
    response_class=FileResponse,
    responses={200: {"content": {"image/jpeg": {}}}},
)
async def create_korean_meme(
    content_creator: Annotated[MemeImageCreator, Depends(inject_meme_image_creator)],
    request: CreateContentRequest,
) -> FileResponse:
    image_path = await content_creator.create(request.created_at)

    return FileResponse(
        path=image_path,
        media_type="image/jpeg",
    )


@router.delete(
    "/{date}/{language_code}/{ImageType}",
    status_code=204,
)
async def delete_content(
    date: datetime,
    language_code: LanguageCode,
    image_type: ImageType,
) -> None:
    """
    Delete content for the given date and language code.
    """
    if image_manager.is_exist(
        language_code=language_code, date=date, image_type=image_type
    ):
        os.remove(
            image_manager.find_image_path_by(
                language_code=language_code, date=date, image_type=image_type
            )
        )


@router.post("/memes/analyze", status_code=status.HTTP_201_CREATED)
async def analyze_meme(
    meme_candidate: MemeCandidate,
    repository: Annotated[MemeRepository, Depends(inject_meme_repository)],
) -> ApiResponse[int]:
    analysis_result = await meme_analyzer.analyze_meme(meme_candidate.image_url)
    save_id = await repository.save(meme_candidate, analysis_result)

    return ApiResponse(
        status_code=status.HTTP_201_CREATED, status_message="CREATED", content=save_id
    )


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
