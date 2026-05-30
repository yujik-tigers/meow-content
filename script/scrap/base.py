from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from script.schema import RawData

T = TypeVar("T", bound=RawData)


class RawDataScraper(ABC, Generic[T]):

    @abstractmethod
    async def scrap(self) -> list[T]: ...
