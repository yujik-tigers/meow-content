from abc import ABC, abstractmethod
from collections.abc import Sequence

from app.repository.mysql.models import Content


class RawDataUploader(ABC):

    @abstractmethod
    async def upload(self, data: Sequence[Content]) -> None: ...
