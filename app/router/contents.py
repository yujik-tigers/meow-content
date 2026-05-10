import logging
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from starlette import status

from app.client.reddit_client import RedditClient
from app.content import meme_analyzer
from app.content.enums import MemeStatus
from app.dependencies import (
    inject_meme_repository,
    inject_reddit_client,
)
from app.exceptions import NoApprovedMemeError
from app.repository import MemeRepository
from app.schema.common import ApiResponse
from app.schema.contents import (
    MemeCandidate,
    MemeContent,
    MemeSaveData,
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


# 동시성 문제 있음
@router.get("/memes")
async def fetch_daily_meme(
    date: date, repository: Annotated[MemeRepository, Depends(inject_meme_repository)]
) -> ApiResponse[MemeContent | None]:
    meme_content = await repository.get_by_used_at(date)
    if meme_content is None:
        approved_meme = next(
            iter(await repository.fetch_by_statuses([MemeStatus.APPROVED], 0, 1)), None
        )
        if not approved_meme:
            raise NoApprovedMemeError()

        assert approved_meme.id is not None
        meme_content = await repository.mark_as_used(approved_meme.id, date)
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
            await repository.save(
                MemeSaveData(
                    img_url=candidate.image_url,
                    meme_text=result.meme_text,
                    meme_text_translation=result.meme_text_translation,
                    author=candidate.author,
                    source=candidate.source,
                    expressions=result.expressions,
                    translation=result.translation,
                    background=result.background,
                )
            )
        except Exception as e:
            logger.error(f"Failed to process {candidate.image_url}: {e}")


@router.post("/memes/analyze", status_code=status.HTTP_201_CREATED)
async def analyze_meme(
    meme_candidate: MemeCandidate,
    repository: Annotated[MemeRepository, Depends(inject_meme_repository)],
) -> ApiResponse[int]:
    analysis_result = await meme_analyzer.analyze_meme(meme_candidate.image_url)
    save_id = await repository.save(
        MemeSaveData(
            img_url=meme_candidate.image_url,
            meme_text=analysis_result.meme_text,
            meme_text_translation=analysis_result.meme_text_translation,
            author=meme_candidate.author,
            source=meme_candidate.source,
            expressions=analysis_result.expressions,
            translation=analysis_result.translation,
            background=analysis_result.background,
        )
    )

    return ApiResponse(
        status_code=status.HTTP_201_CREATED, status_message="CREATED", content=save_id
    )
