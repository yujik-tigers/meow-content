from abc import ABC, abstractmethod
from typing import Generic, TypeVar

T = TypeVar("T")


class RawDataUploader(ABC, Generic[T]):

    @abstractmethod
    async def upload(self, data: T) -> bool: ...
