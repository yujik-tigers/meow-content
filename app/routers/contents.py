import io
import os
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends
from starlette import status

from app.contents import meme_analyzer
from app.db.repository import MemeRepository
from app.dependencies import (
    inject_meme_repository,
)
from app.schemas.common import ApiResponse
from app.schemas.contents import MemeCandidate, MemeContent

router = APIRouter(prefix="/contents", tags=["contents"])


@router.get("/memes")
async def fetch_meme(
    repository: Annotated[MemeRepository, Depends(inject_meme_repository)], date: date
) -> ApiResponse[MemeContent]:
    meme_content = await repository.fetch_approved_and_mark_used(date)
    return ApiResponse(status.HTTP_200_OK, "OK", meme_content)


@router.post("/memes/analyze", status_code=status.HTTP_201_CREATED)
async def analyze_meme(
    repository: Annotated[MemeRepository, Depends(inject_meme_repository)],
    meme_candidate: MemeCandidate,
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
