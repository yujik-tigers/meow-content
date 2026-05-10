import functools
from collections.abc import Callable
from datetime import date
from typing import Any

from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.content.enums import MemeStatus
from app.exceptions import MemeNotFoundError
from app.repository.base import MemeRepository
from app.repository.mysql.models import MemeRecord
from app.schema.contents import MemeContent, MemeSaveData


def transactional(func: Callable[..., Any]) -> Callable[..., Any]:
    @functools.wraps(func)
    async def wrapper(self: "MySQLMemeRepository", *args: Any, **kwargs: Any) -> Any:
        try:
            result = await func(self, *args, **kwargs)
            await self._session.commit()
            return result
        except Exception:
            await self._session.rollback()
            raise

    return wrapper


class MySQLMemeRepository(MemeRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @transactional
    async def save(self, data: MemeSaveData) -> int:
        record = MemeRecord(
            img_url=data.img_url,
            meme_text=data.meme_text,
            meme_text_translation=data.meme_text_translation,
            author=data.author,
            source=data.source,
            expressions=data.expressions,
            translation=data.translation,
            background=data.background,
        )
        self._session.add(record)
        await self._session.flush()

        assert record.id is not None
        return record.id

    async def get_by_used_at(self, used_at: date) -> MemeContent | None:
        result = await self._session.exec(
            select(MemeRecord)
            .where(col(MemeRecord.status) == MemeStatus.USED)
            .where(col(MemeRecord.used_at) == used_at)
            .limit(1)
        )
        record = result.first()
        if record is None:
            return None

        return record.to_content()

    @transactional
    async def mark_as_used(self, meme_id: int, used_at: date) -> MemeContent:
        record = await self._session.get(MemeRecord, meme_id)
        if record is None:
            raise MemeNotFoundError(meme_id)
        record.status = MemeStatus.USED
        record.used_at = used_at
        return record.to_content()

    @transactional
    async def update_background(self, meme_id: int, background: str) -> None:
        record = await self._session.get(MemeRecord, meme_id)
        if record is None:
            raise MemeNotFoundError(meme_id)
        record.background = background

    @transactional
    async def update_status(self, meme_id: int, status: MemeStatus) -> None:
        record = await self._session.get(MemeRecord, meme_id)
        if record is None:
            raise MemeNotFoundError(meme_id)
        record.status = status

    async def fetch_by_statuses(
        self, statuses: list[MemeStatus], offset: int, limit: int
    ) -> list[MemeContent]:
        result = await self._session.exec(
            select(MemeRecord)
            .where(col(MemeRecord.status).in_(statuses))
            .order_by(col(MemeRecord.id).asc())
            .offset(offset)
            .limit(limit)
        )
        return [record.to_content() for record in result.all()]
