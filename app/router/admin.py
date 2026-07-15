import logging
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Body, Depends
from starlette import status

from app.analyzer.factory import AnalyzerFactory
from app.dependencies import inject_repository, inject_usage_repository
from app.enums import ContentStatus, ContentType
from app.image_generator.factory import ImageGeneratorFactory
from app.repository.base import ContentRepository, TokenUsageRepository
from app.schema.common import ApiResponse
from app.schema.content import (
    Content,
    GenerateImageRequest,
    ReanalyzeContentField,
    RegenerateImageRequest,
    ScrapingRequest,
    UpdateContentStatusRequest,
)
from app.schema.usage import UsageCostSummary
from app.scrap.factory import ScraperFactory
from app.usage.pricing import compute_cost

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
    items = await repository.fetch_contents_by(
        content_status, content_type, page_index * page_size, page_size
    )
    return ApiResponse(status.HTTP_200_OK, "OK", items)


@router.post("/contents/{content_id}/analyze")
async def analyze_raw_content(
    content_id: int,
    content_type: Annotated[ContentType, Body()],
    repository: Annotated[ContentRepository, Depends(inject_repository)],
) -> ApiResponse[Content]:
    item = await repository.get_content_by(content_id)
    analyzer = AnalyzerFactory.get_analyzer(content_type)
    analyzed_content = await analyzer.analyze_raw_content(item)
    await repository.update_content(analyzed_content)
    return ApiResponse(status.HTTP_200_OK, "OK", analyzed_content)


@router.post("/contents/{content_id}/image")
async def generate_image_for_content(
    content_id: int,
    request: GenerateImageRequest,
    repository: Annotated[ContentRepository, Depends(inject_repository)],
) -> ApiResponse[Content]:
    item = await repository.get_content_by(content_id)
    image_generator = ImageGeneratorFactory.get_image_generator(
        request.content_type, request.model
    )
    image_generated_content = await image_generator.generate(item)
    await repository.update_content(image_generated_content)
    return ApiResponse(status.HTTP_200_OK, "OK", image_generated_content)


@router.post("/contents/{content_id}/image/regenerate")
async def regenerate_image_for_content(
    content_id: int,
    request: RegenerateImageRequest,
    repository: Annotated[ContentRepository, Depends(inject_repository)],
) -> ApiResponse[Content]:
    item = await repository.get_content_by(content_id)
    image_generator = ImageGeneratorFactory.get_image_generator(
        request.content_type, request.model
    )
    image_regenerated_content = await image_generator.regenerate(
        item, request.prompt, request.regenerate_type
    )
    await repository.update_content(image_regenerated_content)
    return ApiResponse(status.HTTP_200_OK, "OK", image_regenerated_content)


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
    content_type: Annotated[ContentType, Body()],
    repository: Annotated[ContentRepository, Depends(inject_repository)],
) -> None:
    item = await repository.get_content_by(content_id)
    analyzer = AnalyzerFactory.get_analyzer(content_type)
    updated = await analyzer.reanalyze_content_field(item, request)
    await repository.update_content(updated)


@router.get("/usage/cost")
async def get_usage_cost(
    start: datetime,
    end: datetime,
    usage_repository: Annotated[TokenUsageRepository, Depends(inject_usage_repository)],
    apply_free_tier: bool = False,
) -> ApiResponse[list[UsageCostSummary]]:
    aggregates = await usage_repository.aggregate_by(start, end)
    summaries = [
        UsageCostSummary(
            period=aggregate.period,
            model=aggregate.model,
            request_count=aggregate.request_count,
            input_tokens_sum=aggregate.input_tokens_sum,
            output_tokens_sum=aggregate.output_tokens_sum,
            cost=compute_cost(
                aggregate.model,
                aggregate.input_tokens_sum,
                aggregate.output_tokens_sum,
                apply_free_tier=apply_free_tier,
            ),
        )
        for aggregate in aggregates
    ]
    return ApiResponse(status.HTTP_200_OK, "OK", summaries)


@router.post("/scrap", status_code=status.HTTP_204_NO_CONTENT)
async def trigger_scraping(
    request: ScrapingRequest,
    repository: Annotated[ContentRepository, Depends(inject_repository)],
) -> None:
    scraper = ScraperFactory.get_scraper(request.content_type)
    contents = await scraper.scrape()
    await repository.create_contents(contents)
