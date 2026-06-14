from collections.abc import AsyncGenerator, AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession

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
