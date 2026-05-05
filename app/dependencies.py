from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from app.contents.quote_image_creator import QuoteImageCreator, quote_image_creator
from app.db.engine import AsyncSessionLocal
from app.db.repository import MemeRepository


async def inject_quote_image_creator() -> QuoteImageCreator:
    return quote_image_creator


async def inject_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


async def inject_meme_repository(
    session: Annotated[AsyncSession, Depends(inject_db_session)],
) -> MemeRepository:
    return MemeRepository(session)
