from dataclasses import dataclass

from app.repository.mysql.models import Content, RedditMeme


@dataclass(frozen=True)
class RedditMemeRaw:
    image_url: str
    author: str
    title: str

    def to_entity(self) -> Content:
        return RedditMeme(
            image_url=self.image_url,
            author=self.author,
            title=self.title,
        )
