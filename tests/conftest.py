import os

os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")
os.environ.setdefault("GEMINI_API_KEY", "test-gemini-key")
os.environ.setdefault("CLOUDFLARE_API_KEY", "test-cf-key")
os.environ.setdefault("CLOUDFLARE_ACCOUNT_ID", "test-cf-account")
os.environ.setdefault("CLOUDFLARE_IMAGE_GEN_MODEL", "test-model")
os.environ.setdefault("MEME_FONT_PATH", "/fake/font.ttf")
os.environ.setdefault("MEME_FONT_PATH_KOR", "/fake/font_kor.ttf")
os.environ.setdefault("MYSQL_URL", "mysql+aiomysql://test:test@localhost/test_db")
os.environ.setdefault("SCHEDULER_HOUR", "9")
os.environ.setdefault("SCHEDULER_MINUTE", "0")
os.environ.setdefault("SCRAPER_DAY_OF_WEEK", "mon")
os.environ.setdefault("SCRAPER_HOUR", "6")
os.environ.setdefault("SCRAPER_MINUTE", "0")
os.environ.setdefault("REDDIT_MEME_COUNT", "20")
os.environ.setdefault("REDDIT_TIME_FILTER", "week")
os.environ.setdefault("LANGSMITH_TRACING", "false")
os.environ.setdefault("LANGSMITH_ENDPOINT", "http://fake.langsmith.dev")
os.environ.setdefault("LANGSMITH_API_KEY", "test-langsmith-key")
os.environ.setdefault("LANGSMITH_PROJECT", "test-project")
os.environ.setdefault("AWS_ACCESS_KEY_ID", "test-access-key")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "test-secret-key")
os.environ.setdefault("AWS_REGION", "us-east-1")
os.environ.setdefault("AWS_S3_BUCKET_NAME", "test-bucket")

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.analyzer.base import ContentAnalyzer
from app.enums import ContentStatus, ContentType
from app.image_generator.base import ImageGenerator
from app.repository.base import ContentRepository, TokenUsageRepository
from app.schema.content import Content


@pytest.fixture
def make_content():
    def _make(
        id: int = 1,
        type: ContentType = ContentType.REDDIT_MEME,
        status: ContentStatus = ContentStatus.RAW,
        content: str | None = "Turns out, cats sit on your stuff",
        content_translation: str | None = "알고 보니, 고양이가 네 물건 위에 앉아",
        expression: str | None = "turns out",
        expression_translation: str | None = "알고 보니",
        background: str | None = "배경 설명",
        created_at: datetime = datetime(2024, 1, 1, 0, 0),
        image_url: str | None = "https://example.com/cat.jpg",
        author: str | None = "test_user",
        title: str | None = "Cat Meme",
    ) -> Content:
        return Content(
            id=id,
            type=type,
            status=status,
            content=content,
            content_translation=content_translation,
            expression=expression,
            expression_translation=expression_translation,
            background=background,
            created_at=created_at,
            image_url=image_url,
            author=author,
            title=title,
        )

    return _make


@pytest.fixture
def mock_repository() -> AsyncMock:
    mock = AsyncMock(spec=ContentRepository)
    return mock


@pytest.fixture
def mock_analyzer() -> AsyncMock:
    return AsyncMock(spec=ContentAnalyzer)


@pytest.fixture
def mock_image_generator() -> AsyncMock:
    return AsyncMock(spec=ImageGenerator)


@pytest.fixture
def mock_usage_repository() -> AsyncMock:
    return AsyncMock(spec=TokenUsageRepository)


@pytest.fixture
async def client(
    mock_repository, mock_analyzer, mock_image_generator, mock_usage_repository
):
    from app.dependencies import inject_repository, inject_usage_repository
    from app.main import app

    app.dependency_overrides[inject_repository] = lambda: mock_repository
    app.dependency_overrides[inject_usage_repository] = lambda: mock_usage_repository

    with (
        patch("app.main.create_tables", new=AsyncMock()),
        patch(
            "app.main.create_scheduler",
            return_value=MagicMock(start=MagicMock(), shutdown=MagicMock()),
        ),
        patch(
            "app.router.admin.ImageGeneratorFactory.get_image_generator",
            return_value=mock_image_generator,
        ),
        patch(
            "app.router.admin.AnalyzerFactory.get_analyzer",
            return_value=mock_analyzer,
        ),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as c:
            yield c

    app.dependency_overrides.clear()
