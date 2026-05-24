from abc import ABC, abstractmethod
from collections.abc import Sequence

from app.repository.mysql._models import ContentRecord


class RawDataUploader(ABC):

    @abstractmethod
    async def upload(self, data: Sequence[ContentRecord]) -> None: ...
