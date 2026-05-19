from abc import ABC, abstractmethod
from typing import Generic, TypeVar

T = TypeVar("T")


class RawDataScraper(ABC, Generic[T]):

    @abstractmethod
    async def scrap(self) -> list[T]: ...
