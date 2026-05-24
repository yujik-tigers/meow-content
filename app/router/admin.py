import logging
from typing import Annotated

from fastapi import APIRouter, Depends
from starlette import status

from app.analyzer.base import ContentAnalyzer
from app.dependencies import inject_analyzer, inject_repository
from app.enums import ContentStatus, ContentType
from app.repository.base import ContentRepository
from app.schema.common import ApiResponse
from app.schema.content import (
    Content,
    ReanalyzeContentField,
    UpdateContentStatusRequest,
)

router = APIRouter(prefix="/admin", tags=["admin"])
logger = logging.getLogger(__name__)


@router.get("/contents")
async def list_contents(
    content_status: ContentStatus,
    content_type: ContentType,
    repository: Annotated[ContentRepository, Depends(inject_repository)],
    page_index: int = 0,
    page_size: int = 20,
) -> ApiResponse[list[Content]]:
    items = await repository.fetch_admin_contents_by(
        content_status, content_type, page_index * page_size, page_size
    )
    return ApiResponse(status.HTTP_200_OK, "OK", items)


@router.post("/contents/{content_id}/analyze")
async def analyze_raw_content(
    content_id: int,
    repository: Annotated[ContentRepository, Depends(inject_repository)],
    analyzer: Annotated[ContentAnalyzer, Depends(inject_analyzer)],
) -> ApiResponse[Content]:
    item = await repository.get_admin_content_by(content_id)
    analyzed_content = await analyzer.analyze_raw_content(item)
    await repository.update_content(analyzed_content)
    return ApiResponse(status.HTTP_200_OK, "OK", analyzed_content)


@router.patch("/contents/{content_id}/status", status_code=status.HTTP_204_NO_CONTENT)
async def update_content_status(
    content_id: int,
    request: UpdateContentStatusRequest,
    repository: Annotated[ContentRepository, Depends(inject_repository)],
) -> None:
    await repository.update_status(content_id, request.to_status)


@router.patch("/contents/{content_id}", status_code=status.HTTP_204_NO_CONTENT)
async def update_content(
    content_id: int,
    request: list[ReanalyzeContentField],
    repository: Annotated[ContentRepository, Depends(inject_repository)],
    analyzer: Annotated[ContentAnalyzer, Depends(inject_analyzer)],
) -> None:
    item = await repository.get_admin_content_by(content_id)
    updated = await analyzer.reanalyze_content_field(item, request)
    await repository.update_content(updated)
