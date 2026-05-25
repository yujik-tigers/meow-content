from abc import ABC, abstractmethod
from datetime import date

from app.enums import ContentStatus, ContentType
from app.schema.content import Content


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
