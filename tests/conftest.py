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
from app.repository.base import ContentRepository
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
async def client(mock_repository, mock_analyzer, mock_image_generator):
    from app.dependencies import inject_analyzer, inject_image_generator, inject_repository
    from app.main import app

    app.dependency_overrides[inject_repository] = lambda: mock_repository
    app.dependency_overrides[inject_analyzer] = lambda: mock_analyzer
    app.dependency_overrides[inject_image_generator] = lambda: mock_image_generator

    with (
        patch("app.main.create_tables", new=AsyncMock()),
        patch(
            "app.main.create_scheduler",
            return_value=MagicMock(start=MagicMock(), shutdown=MagicMock()),
        ),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as c:
            yield c

    app.dependency_overrides.clear()
