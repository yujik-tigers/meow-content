from datetime import date, datetime
from zoneinfo import ZoneInfo

from sqlalchemy import Column, Text
from sqlmodel import Field, SQLModel

from app.content.enums import ContentType, LiteralType, MemeStatus
from app.schema.contents import MemeContent


class MemeRecord(SQLModel, table=True):
    __tablename__ = "meme_record"  # pyright: ignore[reportAssignmentType]

    id: int | None = Field(default=None, primary_key=True)
    img_url: str = Field(sa_column=Column(Text))
    meme_text: str
    author: str = Field(max_length=200)
    source: str = Field(max_length=200)
    meme_text_translation: str
    expressions: str = Field(max_length=200)
    translation: str = Field(max_length=200)
    background: str = Field(sa_column=Column(Text))
    status: MemeStatus = Field(default=MemeStatus.RAW, max_length=20)
    used_at: date | None = Field(default=None)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(ZoneInfo("Asia/Seoul"))
    )

    def to_content(self) -> MemeContent:
        return MemeContent(
            id=self.id,  # type: ignore[arg-type]
            image_url=self.img_url,
            meme_text=self.meme_text,
            meme_text_translation=self.meme_text_translation,
            source=self.source,
            author=self.author,
            expressions=self.expressions,
            translation=self.translation,
            background=self.background,
            status=self.status,
            used_at=self.used_at,
        )


class Content(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    type: ContentType = Field(max_length=50)
    status: MemeStatus = Field(default=MemeStatus.RAW, max_length=20)
    content: str | None = Field(default=None, sa_column=Column(Text))
    content_translation: str | None = Field(default=None, sa_column=Column(Text))
    expression: str | None = Field(default=None, max_length=200)
    expression_translation: str | None = Field(default=None, max_length=200)
    background: str | None = Field(default=None, sa_column=Column(Text))

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(ZoneInfo("Asia/Seoul"))
    )
    used_at: date | None = Field(default=None)

    # RedditMeme / Quote / LiteralQuote
    author: str | None = Field(default=None, max_length=200)
    # RedditMeme
    image_url: str | None = Field(default=None, sa_column=Column(Text))
    # RedditMeme / LiteralQuote
    title: str | None = Field(default=None, max_length=200)
    # LiteralQuote
    literal_type: LiteralType | None = Field(default=None, max_length=20)


class RedditMeme:
    def __new__(cls, image_url: str, author: str, title: str, **kwargs) -> Content:
        return Content(
            type=ContentType.REDDIT_MEME,
            image_url=image_url,
            author=author,
            title=title,
            **kwargs,
        )


class Quote:
    def __new__(cls, content: str, author: str, **kwargs) -> Content:
        return Content(
            type=ContentType.QUOTE,
            content=content,
            author=author,
            **kwargs,
        )


class LiteralQuote:
    def __new__(
        cls, content: str, author: str, literal_type: LiteralType, title: str, **kwargs
    ) -> Content:
        return Content(
            type=ContentType.LiteralQuote,
            content=content,
            author=author,
            literal_type=literal_type,
            title=title,
            **kwargs,
        )


class Fact:
    def __new__(cls, content: str, **kwargs) -> Content:
        return Content(
            type=ContentType.FACT,
            content=content,
            **kwargs,
        )
