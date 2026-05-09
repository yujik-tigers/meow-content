import logging
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from starlette import status

from app.client.reddit_client import RedditClient
from app.content import meme_analyzer
from app.content.enums import MemeStatus
from app.db.repository import MemeRepository
from app.dependencies import (
    inject_meme_repository,
    inject_reddit_client,
)
from app.schema.common import ApiResponse
from app.schema.contents import (
    MemeCandidate,
    MemeContent,
    TriggerScrapingRequest,
    UpdateMemeBackgroundRequest,
    UpdateMemeStatusRequest,
)

router = APIRouter(prefix="/contents", tags=["contents"])
logger = logging.getLogger(__name__)


@router.get("/memes/search")
async def list_memes(
    statuses: Annotated[list[MemeStatus], Query(alias="status")],
    repository: Annotated[MemeRepository, Depends(inject_meme_repository)],
    page_index: int = 0,
    page_size: int = 20,
) -> ApiResponse[list[MemeContent]]:
    items = await repository.fetch_by_statuses(
        statuses, page_index * page_size, page_size
    )
    return ApiResponse(status.HTTP_200_OK, "OK", items)


@router.get("/memes")
async def fetch_daily_meme(
    date: date, repository: Annotated[MemeRepository, Depends(inject_meme_repository)]
) -> ApiResponse[MemeContent]:
    meme_content = await repository.get_approved_meme_by(date)
    return ApiResponse(status.HTTP_200_OK, "OK", meme_content)


@router.patch("/memes/{meme_id}/background", status_code=status.HTTP_204_NO_CONTENT)
async def update_meme_background(
    meme_id: int,
    request: UpdateMemeBackgroundRequest,
    repository: Annotated[MemeRepository, Depends(inject_meme_repository)],
) -> None:
    await repository.update_background(meme_id, request.background)


@router.patch("/memes/{meme_id}/status", status_code=status.HTTP_204_NO_CONTENT)
async def update_meme_status(
    meme_id: int,
    request: UpdateMemeStatusRequest,
    repository: Annotated[MemeRepository, Depends(inject_meme_repository)],
) -> None:
    await repository.update_status(meme_id, request.status)


@router.post("/memes/scrape", status_code=status.HTTP_204_NO_CONTENT)
async def trigger_scraping(
    request: TriggerScrapingRequest,
    reddit_client: Annotated[RedditClient, Depends(inject_reddit_client)],
    repository: Annotated[MemeRepository, Depends(inject_meme_repository)],
) -> None:
    candidates = await reddit_client.fetch_cat_memes(request.count)
    for candidate in candidates:
        try:
            result = await meme_analyzer.analyze_meme(candidate.image_url)
            await repository.save(candidate, result)
        except Exception as e:
            logger.error(f"Failed to process {candidate.image_url}: {e}")


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
