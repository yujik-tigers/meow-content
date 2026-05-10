from abc import ABC, abstractmethod
from datetime import date

from app.content.enums import MemeStatus
from app.schema.contents import MemeContent, MemeSaveData


class MemeRepository(ABC):
    @abstractmethod
    async def save(self, data: MemeSaveData) -> int: ...

    @abstractmethod
    async def get_by_used_at(self, used_at: date) -> MemeContent | None: ...

    @abstractmethod
    async def mark_as_used(self, meme_id: int, used_at: date) -> MemeContent: ...

    @abstractmethod
    async def update_background(self, meme_id: int, background: str) -> None: ...

    @abstractmethod
    async def update_status(self, meme_id: int, status: MemeStatus) -> None: ...

    @abstractmethod
    async def fetch_by_statuses(
        self, statuses: list[MemeStatus], offset: int, limit: int
    ) -> list[MemeContent]: ...
