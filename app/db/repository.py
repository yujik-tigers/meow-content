import functools
from collections.abc import Callable
from datetime import date
from typing import Any

from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.content.enums import MemeStatus
from app.content.meme_analyzer import MemeAnalyzeResult
from app.db.models import MemeRecord
from app.exceptions import MemeNotFoundError, NoApprovedMemeError
from app.schema.contents import MemeCandidate, MemeContent


def transactional(func: Callable[..., Any]) -> Callable[..., Any]:
    @functools.wraps(func)
    async def wrapper(self: "MemeRepository", *args: Any, **kwargs: Any) -> Any:
        try:
            result = await func(self, *args, **kwargs)
            await self._session.commit()
            return result
        except Exception:
            await self._session.rollback()
            raise

    return wrapper


class MemeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @transactional
    async def save(
        self, meme_candidate: MemeCandidate, result: MemeAnalyzeResult
    ) -> int:
        record = MemeRecord(
            img_url=meme_candidate.image_url,
            meme_text=result.meme_text,
            meme_text_translation=result.meme_text_translation,
            author=meme_candidate.author,
            source=meme_candidate.source,
            expressions=result.expressions,
            translation=result.translation,
            background=result.background,
        )
        self._session.add(record)
        await self._session.flush()

        assert record.id is not None
        return record.id

    @transactional
    async def get_approved_meme_by(self, used_at: date) -> MemeContent:
        used_result = await self._session.exec(
            select(MemeRecord)
            .where(col(MemeRecord.status) == MemeStatus.USED)
            .where(col(MemeRecord.used_at) == used_at)
            .limit(1)
        )
        record = used_result.first()

        if record is None:
            record = await self.get_approved_meme_and_mark_used(used_at)

        return MemeContent(
            image_url=record.img_url,
            meme_text=record.meme_text,
            meme_text_translation=record.meme_text_translation,
            source=record.source,
            author=record.author,
            expressions=record.expressions,
            translation=record.translation,
            background=record.background,
            status=record.status,
            used_at=record.used_at,
        )

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
        return [
            MemeContent(
                id=record.id,  # type: ignore[arg-type]
                image_url=record.img_url,
                meme_text=record.meme_text,
                meme_text_translation=record.meme_text_translation,
                source=record.source,
                author=record.author,
                expressions=record.expressions,
                translation=record.translation,
                background=record.background,
                status=record.status,
                used_at=record.used_at,
            )
            for record in result.all()
        ]

    async def get_approved_meme_and_mark_used(self, used_at: date) -> MemeRecord:
        approved_result = await self._session.exec(
            select(MemeRecord)
            .where(col(MemeRecord.status) == MemeStatus.APPROVED)
            .limit(1)
        )
        record = approved_result.first()
        if record is None:
            raise NoApprovedMemeError()

        record.status = MemeStatus.USED
        record.used_at = used_at

        return record
