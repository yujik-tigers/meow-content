from abc import ABC, abstractmethod
from datetime import date, datetime

from app.enums import ContentStatus, ContentType
from app.schema.content import Content
from app.schema.usage import UsageAggregate


class ContentRepository(ABC):

    @abstractmethod
    async def update_status(self, content_id: int, status: ContentStatus) -> None: ...

    @abstractmethod
    async def get_reserved_content_at(self, used_at: date) -> Content: ...

    @abstractmethod
    async def fetch_contents_by(
        self, status: ContentStatus, content_type: ContentType, offset: int, limit: int
    ) -> list[Content]: ...

    @abstractmethod
    async def get_content_by(self, content_id: int) -> Content: ...

    @abstractmethod
    async def update_content(self, content: Content) -> None: ...

    @abstractmethod
    async def reserve_daily_content(self, used_at: date) -> Content: ...


class TokenUsageRepository(ABC):

    @abstractmethod
    async def record(self, model: str, input_tokens: int, output_tokens: int) -> None: ...

    @abstractmethod
    async def aggregate_by(
        self, start: datetime, end: datetime
    ) -> list[UsageAggregate]: ...
