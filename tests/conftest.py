import asyncio
import os

# 실제 DB 테스트는 개발용 meow DB가 아닌 전용 meow_test DB를 사용한다.
# setdefault가 아닌 강제 할당: 셸/.env의 MYSQL_URL이 테스트로 새어 들어오는 것을 차단.
TEST_MYSQL_URL = os.environ.get(
    "TEST_MYSQL_URL", "mysql+aiomysql://root:root@127.0.0.1:3306/meow_test"
)
os.environ["MYSQL_URL"] = TEST_MYSQL_URL

os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")
os.environ.setdefault("GEMINI_API_KEY", "test-gemini-key")
os.environ.setdefault("CLOUDFLARE_API_KEY", "test-cf-key")
os.environ.setdefault("CLOUDFLARE_ACCOUNT_ID", "test-cf-account")
os.environ.setdefault("CLOUDFLARE_IMAGE_GEN_MODEL", "test-model")
os.environ.setdefault("MEME_FONT_PATH", "/fake/font.ttf")
os.environ.setdefault("MEME_FONT_PATH_KOR", "/fake/font_kor.ttf")
os.environ.setdefault("SCHEDULER_HOUR", "9")
os.environ.setdefault("SCHEDULER_MINUTE", "0")
os.environ.setdefault("SCRAPER_DAY_OF_WEEK", "mon")
os.environ.setdefault("SCRAPER_HOUR", "6")
os.environ.setdefault("SCRAPER_MINUTE", "0")
os.environ.setdefault("REDDIT_MEME_COUNT", "20")
os.environ.setdefault("REDDIT_TIME_FILTER", "week")
os.environ.setdefault("QDRANT_FACT_COLLECTION", "test-fact-collection")
os.environ.setdefault("FACT_SIMILARITY_THRESHOLD", "0.9")
os.environ.setdefault("LANGSMITH_TRACING", "false")
os.environ.setdefault("LANGSMITH_ENDPOINT", "http://fake.langsmith.dev")
os.environ.setdefault("LANGSMITH_API_KEY", "test-langsmith-key")
os.environ.setdefault("LANGSMITH_PROJECT", "test-project")
os.environ.setdefault("AWS_ACCESS_KEY_ID", "test-access-key")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "test-secret-key")
os.environ.setdefault("AWS_REGION", "us-east-1")
os.environ.setdefault("AWS_S3_BUCKET_NAME", "test-bucket")
TEST_IMAGE_STORAGE_DIR = "/tmp/meow-content-test-images"
os.environ["IMAGE_STORAGE_DIR"] = TEST_IMAGE_STORAGE_DIR
os.environ.setdefault("MEDIA_BASE_URL", "http://localhost:8000/media")
os.makedirs(TEST_IMAGE_STORAGE_DIR, exist_ok=True)

from collections.abc import AsyncIterator, Callable
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, create_async_engine
from sqlalchemy.pool import NullPool
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from app.analyzer.base import ContentAnalyzer
from app.enums import ContentStatus, ContentType
from app.image_generator.base import ImageGenerator
from app.scrap.base import Scraper
from app.schema.content import Content


@pytest.fixture(scope="session")
def mysql_available() -> bool:
    """meow_test DB를 생성·초기화하고 MySQL 접속 가능 여부를 반환한다 (불가 시 DB 테스트는 skip)."""

    async def _setup() -> None:
        server_url = TEST_MYSQL_URL.rsplit("/", 1)[0] + "/"
        server_engine = create_async_engine(
            server_url, connect_args={"connect_timeout": 3}
        )
        try:
            async with server_engine.connect() as conn:
                await conn.execute(
                    text(
                        "CREATE DATABASE IF NOT EXISTS meow_test "
                        "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                    )
                )
        finally:
            await server_engine.dispose()

        test_engine = create_async_engine(TEST_MYSQL_URL)
        try:
            async with test_engine.begin() as conn:
                await conn.run_sync(SQLModel.metadata.drop_all)
                await conn.run_sync(SQLModel.metadata.create_all)
        finally:
            await test_engine.dispose()

    try:
        asyncio.run(_setup())
    except (OperationalError, OSError, asyncio.TimeoutError):
        return False
    return True


@pytest.fixture
async def db_engine(mysql_available: bool) -> AsyncIterator[AsyncEngine]:
    """테스트 함수의 이벤트 루프 안에서 생성·폐기되는 엔진 (MySQL 미기동 시 skip)."""
    if not mysql_available:
        pytest.skip("MySQL (meow-mysql container) unreachable; skipping DB test")
    engine = create_async_engine(TEST_MYSQL_URL, poolclass=NullPool)
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_connection(db_engine: AsyncEngine) -> AsyncIterator[AsyncConnection]:
    """테스트 전체를 감싸는 outer 트랜잭션 — teardown에서 롤백되어 데이터가 남지 않는다."""
    async with db_engine.connect() as conn:
        transaction = await conn.begin()
        yield conn
        await transaction.rollback()


@pytest.fixture
def db_session_factory(
    db_connection: AsyncConnection,
) -> Callable[[], AsyncSession]:
    """같은 outer 트랜잭션 위에 새 세션을 만드는 팩토리 — commit은 SAVEPOINT만 해제한다."""

    def _factory() -> AsyncSession:
        return AsyncSession(
            bind=db_connection,
            join_transaction_mode="create_savepoint",
            expire_on_commit=False,
        )

    return _factory


@pytest.fixture
async def db_session(
    db_session_factory: Callable[[], AsyncSession],
) -> AsyncIterator[AsyncSession]:
    """롤백 격리된 실제 DB 세션."""
    session = db_session_factory()
    yield session
    await session.close()


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
def mock_analyzer() -> AsyncMock:
    return AsyncMock(spec=ContentAnalyzer)


@pytest.fixture
def mock_image_generator() -> AsyncMock:
    return AsyncMock(spec=ImageGenerator)


@pytest.fixture
def mock_scraper() -> AsyncMock:
    return AsyncMock(spec=Scraper)


@pytest.fixture
async def client(db_session, mock_analyzer, mock_image_generator, mock_scraper):
    """실제 DB 세션이 주입된 API 테스트 클라이언트 — AI/S3/스크래핑 경계만 mock."""
    from app.dependencies import inject_db_session
    from app.main import app

    async def _override_session():
        yield db_session

    app.dependency_overrides[inject_db_session] = _override_session

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
        patch(
            "app.router.admin.ScraperFactory.get_scraper",
            return_value=mock_scraper,
        ),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as c:
            yield c

    app.dependency_overrides.clear()
