from sqlalchemy.ext.asyncio import AsyncSession

from app.contents.meme_analyzer import MemeAnalyzeResult
from app.db.models import MemeRecord
from app.schemas.contents import MemeCandidate


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
