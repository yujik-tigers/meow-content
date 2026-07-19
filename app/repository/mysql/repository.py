import functools
from collections.abc import Callable, Sequence
from datetime import date, datetime
from typing import Any, override

from sqlmodel import col, func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.enums import ContentStatus, ContentType
from app.exceptions import ContentNotFoundError, NoApprovedContentError
from app.repository.base import ContentRepository, TokenUsageRepository
from app.repository.mysql._models import ContentRecord, TokenUsageRecord
from app.schema.content import Content, NewContent
from app.schema.usage import UsageAggregate


_DAILY_CONTENT_ROTATION: dict[int, ContentType] = {
    0: ContentType.REDDIT_MEME,
    1: ContentType.QUOTE,
    2: ContentType.LiteralQuote,
}


def transactional(fn: Callable[..., Any]) -> Callable[..., Any]:
    @functools.wraps(fn)
    async def wrapper(self, *args: Any, **kwargs: Any) -> Any:
        try:
            result = await fn(self, *args, **kwargs)
            await self._session.commit()
            return result
        except Exception:
            await self._session.rollback()
            raise

    return wrapper


class MySQLContentRepository(ContentRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @override
    @transactional
    async def create_contents(self, contents: Sequence[NewContent]) -> int:
        image_urls = [c.image_url for c in contents if c.image_url]
        existing_urls: set[str] = set()
        if image_urls:
            result = await self._session.exec(
                select(col(ContentRecord.image_url)).where(
                    col(ContentRecord.image_url).in_(image_urls)
                )
            )
            existing_urls = {url for url in result.all() if url}

        quote_texts = [
            c.content
            for c in contents
            if c.type in (ContentType.QUOTE, ContentType.LiteralQuote) and c.content
        ]
        existing_contents: set[str] = set()
        if quote_texts:
            result = await self._session.exec(
                select(col(ContentRecord.content)).where(
                    col(ContentRecord.content).in_(quote_texts)
                )
            )
            existing_contents = {text for text in result.all() if text}

        new_records = []
        for content in contents:
            if content.image_url and content.image_url in existing_urls:
                continue
            if content.content in existing_contents:
                continue
            new_records.append(self._to_new_record(content))

        self._session.add_all(new_records)
        return len(new_records)

    @override
    @transactional
    async def update_status(self, content_id: int, status: ContentStatus) -> None:
        record = await self._session.get(ContentRecord, content_id)
        if record is None:
            raise ContentNotFoundError(content_id)
        record.status = status

    @override
    async def fetch_contents_by(
        self, status: ContentStatus, content_type: ContentType, offset: int, limit: int
    ) -> list[Content]:
        result = await self._session.exec(
            select(ContentRecord)
            .where(col(ContentRecord.status) == status)
            .where(col(ContentRecord.type) == content_type)
            .order_by(col(ContentRecord.id).asc())
            .offset(offset)
            .limit(limit)
        )
        return [record.to_content() for record in result.all()]

    @override
    @transactional
    async def update_content(self, content: Content) -> None:
        await self._session.merge(self._to_record(content))

    @override
    async def get_reserved_content_at(self, used_at: date) -> Content:
        result = await self._session.exec(
            select(ContentRecord)
            .where(col(ContentRecord.status) == ContentStatus.USED)
            .where(col(ContentRecord.used_at) == used_at)
            .limit(1)
        )
        record = result.first()
        if record is None:
            raise NoApprovedContentError()
        return record.to_content()

    @override
    async def get_content_by(self, content_id: int) -> Content:
        record = await self._session.get(ContentRecord, content_id)
        if record is None:
            raise ContentNotFoundError(content_id)
        return record.to_content()

    @override
    @transactional
    async def reserve_daily_content(self, used_at: date) -> Content:
        content_type = _DAILY_CONTENT_ROTATION[used_at.day % 3]

        result = await self._session.exec(
            select(ContentRecord)
            .where(col(ContentRecord.status) == ContentStatus.APPROVED)
            .where(col(ContentRecord.type) == content_type)
            .order_by(col(ContentRecord.id).asc())
            .limit(1)
        )
        record = result.first()
        if record is None:
            raise NoApprovedContentError()
        record.status = ContentStatus.USED
        record.used_at = used_at
        return record.to_content()

    @staticmethod
    def _to_new_record(content: NewContent) -> ContentRecord:
        return ContentRecord(
            type=content.type,
            content=content.content,
            image_url=content.image_url,
            author=content.author[:200] if content.author else None,
            title=content.title[:200] if content.title else None,
            literal_type=content.literal_type,
        )

    @staticmethod
    def _to_record(content: Content) -> ContentRecord:
        return ContentRecord(
            id=content.id,
            type=content.type,
            status=content.status,
            content=content.content,
            content_translation=content.content_translation,
            expression=content.expression,
            expression_translation=content.expression_translation,
            background=content.background,
            created_at=content.created_at,
            used_at=content.used_at,
            image_url=content.image_url,
            author=content.author,
            title=content.title,
            literal_type=content.literal_type,
        )


class MySQLTokenUsageRepository(TokenUsageRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @override
    @transactional
    async def record(self, model: str, input_tokens: int, output_tokens: int) -> None:
        self._session.add(
            TokenUsageRecord(
                model=model, input_tokens=input_tokens, output_tokens=output_tokens
            )
        )

    @override
    async def aggregate_by(
        self, start: datetime, end: datetime
    ) -> list[UsageAggregate]:
        period_expr = func.date_format(TokenUsageRecord.created_at, "%Y-%m-%d")

        result = await self._session.exec(
            select(  # type: ignore[call-overload]
                period_expr.label("period"),
                col(TokenUsageRecord.model).label("model"),
                func.count().label("request_count"),
                func.sum(col(TokenUsageRecord.input_tokens)).label("input_tokens_sum"),
                func.sum(col(TokenUsageRecord.output_tokens)).label(
                    "output_tokens_sum"
                ),
            )
            .where(col(TokenUsageRecord.created_at) >= start)
            .where(col(TokenUsageRecord.created_at) <= end)
            .group_by(period_expr, col(TokenUsageRecord.model))
            .order_by(period_expr)
        )

        return [
            UsageAggregate(
                period=row.period,
                model=row.model,
                request_count=row.request_count,
                input_tokens_sum=int(row.input_tokens_sum),
                output_tokens_sum=int(row.output_tokens_sum),
            )
            for row in result.all()
        ]
