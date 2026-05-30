from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import override

from app.repository.mysql._models import ContentRecord, Quote, RedditMeme


class RawData(ABC):
    @abstractmethod
    def to_entity(self) -> ContentRecord: ...


@dataclass(frozen=True)
class RedditMemeRaw(RawData):
    image_url: str
    author: str
    title: str

    @override
    def to_entity(self) -> ContentRecord:
        return RedditMeme(
            image_url=self.image_url,
            author=self.author,
            title=self.title,
        )


@dataclass(frozen=True)
class DailyQuoteRaw(RawData):
    quote: str
    author: str

    @override
    def to_entity(self) -> ContentRecord:
        return Quote(
            content=self.quote,
            author=self.author,
        )
