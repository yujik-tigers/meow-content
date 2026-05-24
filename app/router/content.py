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
    date: date,
    content_type: ContentType | None,
    repository: Annotated[ContentRepository, Depends(inject_repository)],
) -> ApiResponse[Content]:
    # get에선 가져오기만 하고, 스케줄러에서 approved -> used로 상태 변경하는 방식으로 바꿔야할듯
    reserved_content = await repository.get_reserved_content_at(date)
    return ApiResponse(status.HTTP_200_OK, "OK", reserved_content)
