from dataclasses import dataclass

from app.repository.mysql._models import ContentRecord, RedditMeme


@dataclass(frozen=True)
class RedditMemeRaw:
    image_url: str
    author: str
    title: str

    def to_entity(self) -> ContentRecord:
        return RedditMeme(
            image_url=self.image_url,
            author=self.author,
            title=self.title,
        )
