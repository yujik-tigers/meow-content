from datetime import date

from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.content.enums import MemeStatus
from app.content.meme_analyzer import MemeAnalyzeResult
from app.db.models import MemeRecord
from app.exceptions import MemeNotFoundError, NoApprovedMemeError
from app.schema.contents import MemeCandidate, MemeContent, MemeListItem


class MemeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(
        self, meme_candidate: MemeCandidate, result: MemeAnalyzeResult
    ) -> int:
        record = MemeRecord(
            img_url=meme_candidate.image_url,
            meme_text=result.meme_text,
            author=meme_candidate.author,
            source=meme_candidate.source,
            expressions=result.expressions,
            translation=result.translation,
            background=result.background,
        )
        self._session.add(record)
        await self._session.commit()
        await self._session.refresh(record)

        assert record.id is not None
        return record.id

    async def fetch_approved_and_mark_used(self, used_at: date) -> MemeContent:
        result = await self._session.exec(
            select(MemeRecord)
            .where(col(MemeRecord.status) == MemeStatus.APPROVED)
            .limit(1)
        )
        record = result.first()
        if record is None:
            raise NoApprovedMemeError()

        record.status = MemeStatus.USED
        record.used_at = used_at
        await self._session.commit()

        return MemeContent(
            image_url=record.img_url,
            meme_text=record.meme_text,
            source=record.source,
            author=record.author,
            expressions=record.expressions,
            translation=record.translation,
            background=record.background,
        )

    async def update_status(self, meme_id: int, status: MemeStatus) -> None:
        record = await self._session.get(MemeRecord, meme_id)
        if record is None:
            raise MemeNotFoundError(meme_id)

        record.status = status
        await self._session.commit()

    async def fetch_by_statuses(
        self, statuses: list[MemeStatus], offset: int, limit: int
    ) -> list[MemeListItem]:
        result = await self._session.exec(
            select(MemeRecord)
            .where(col(MemeRecord.status).in_(statuses))
            .order_by(col(MemeRecord.id).asc())
            .offset(offset)
            .limit(limit)
        )
        return [
            MemeListItem(
                id=record.id,  # type: ignore[arg-type]
                image_url=record.img_url,
                meme_text=record.meme_text,
                source=record.source,
                author=record.author,
                expressions=record.expressions,
                translation=record.translation,
                background=record.background,
                status=record.status,
                used_at=record.used_at,
                created_at=record.created_at,
            )
            for record in result.all()
        ]
