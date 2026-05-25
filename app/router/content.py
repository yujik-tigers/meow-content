import logging
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends
from starlette import status

from app.dependencies import (
    inject_repository,
)
from app.enums import ContentType
from app.repository.base import ContentRepository
from app.schema.common import ApiResponse
from app.schema.content import Content

router = APIRouter(prefix="/contents", tags=["contents"])
logger = logging.getLogger(__name__)


@router.get("/")
async def get_daily_content(
    repository: Annotated[ContentRepository, Depends(inject_repository)],
    date: date,
    content_type: ContentType | None = None,
) -> ApiResponse[Content]:
    reserved_content = await repository.get_reserved_content_at(date)
    return ApiResponse(status.HTTP_200_OK, "OK", reserved_content)
