from collections.abc import AsyncGenerator, AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from app.analyzer.base import ContentAnalyzer
from app.analyzer.meme_analyzer import reddit_meme_analyzer
from app.enums import ContentType
from app.repository.base import ContentRepository
from app.repository.mysql.engine import AsyncSessionLocal
from app.repository.mysql.repository import MySQLContentRepository


@asynccontextmanager
async def get_repository() -> AsyncIterator[ContentRepository]:
    async with AsyncSessionLocal() as session:
        yield MySQLContentRepository(session)


async def inject_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


async def inject_repository(
    session: Annotated[AsyncSession, Depends(inject_db_session)],
) -> ContentRepository:
    return MySQLContentRepository(session)


async def inject_analyzer(content_type: ContentType) -> ContentAnalyzer:
    if content_type == ContentType.REDDIT_MEME:
        return reddit_meme_analyzer
    raise ValueError(f"Unsupported content type to analyze: {content_type}")
