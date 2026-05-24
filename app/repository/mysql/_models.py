from datetime import date, datetime
from zoneinfo import ZoneInfo

from sqlalchemy import Column, Text
from sqlmodel import Field, SQLModel

from app.enums import ContentStatus, ContentType, LiteralType
from app.schema.content import Content


class ContentRecord(SQLModel, table=True):
    __tablename__ = "content"  # pyright: ignore[reportAssignmentType]

    id: int | None = Field(default=None, primary_key=True)
    type: ContentType = Field(max_length=50)
    status: ContentStatus = Field(default=ContentStatus.RAW, max_length=20)
    content: str | None = Field(default=None, sa_column=Column(Text))
    content_translation: str | None = Field(default=None, sa_column=Column(Text))
    expression: str | None = Field(default=None, max_length=200)
    expression_translation: str | None = Field(default=None, max_length=200)
    background: str | None = Field(default=None, sa_column=Column(Text))

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(ZoneInfo("Asia/Seoul"))
    )
    used_at: date | None = Field(default=None)
    image_url: str | None = Field(default=None, sa_column=Column(Text))

    # RedditMeme / Quote / LiteralQuote
    author: str | None = Field(default=None, max_length=200)
    # RedditMeme / LiteralQuote
    title: str | None = Field(default=None, max_length=200)
    # LiteralQuote
    literal_type: LiteralType | None = Field(default=None, max_length=20)

    def to_content(self) -> Content:
        return Content(
            id=self.id,  # type: ignore[arg-type]
            type=self.type,
            status=self.status,
            content=self.content,
            content_translation=self.content_translation,
            expression=self.expression,
            expression_translation=self.expression_translation,
            background=self.background,
            created_at=self.created_at,
            used_at=self.used_at,
            image_url=self.image_url,
            author=self.author,
            title=self.title,
            literal_type=self.literal_type,
        )


class RedditMeme:
    def __new__(
        cls, image_url: str, author: str, title: str, **kwargs
    ) -> ContentRecord:
        return ContentRecord(
            type=ContentType.REDDIT_MEME,
            image_url=image_url,
            author=author,
            title=title,
            **kwargs,
        )


class Quote:
    def __new__(cls, content: str, author: str, **kwargs) -> ContentRecord:
        return ContentRecord(
            type=ContentType.QUOTE,
            content=content,
            author=author,
            **kwargs,
        )


class LiteralQuote:
    def __new__(
        cls, content: str, author: str, literal_type: LiteralType, title: str, **kwargs
    ) -> ContentRecord:
        return ContentRecord(
            type=ContentType.LiteralQuote,
            content=content,
            author=author,
            literal_type=literal_type,
            title=title,
            **kwargs,
        )


class Fact:
    def __new__(cls, content: str, **kwargs) -> ContentRecord:
        return ContentRecord(
            type=ContentType.FACT,
            content=content,
            **kwargs,
        )
