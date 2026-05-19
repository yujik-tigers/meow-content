from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from app.repository import MemeRepository
from app.repository.mysql.engine import AsyncSessionLocal
from app.repository.mysql.repository import MySQLMemeRepository


async def inject_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


async def inject_meme_repository(
    session: Annotated[AsyncSession, Depends(inject_db_session)],
) -> MemeRepository:
    return MySQLMemeRepository(session)
