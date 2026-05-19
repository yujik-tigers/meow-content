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
    __mapper_args__ = {"polymorphic_on": "type"}
    type: ContentType = Field(max_length=50)

    id: int | None = Field(default=None, primary_key=True)

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


class RedditMeme(Content, table=False):
    __mapper_args__ = {"polymorphic_identity": ContentType.REDDIT_MEME}

    type: ContentType = Field(default=ContentType.REDDIT_MEME)
    image_url: str = Field(sa_column=Column(Text))
    author: str = Field(max_length=200)
    title: str = Field(max_length=200)


class Quote(Content, table=False):
    __mapper_args__ = {"polymorphic_identity": ContentType.QUOTE}

    type: ContentType = Field(default=ContentType.QUOTE)
    author: str = Field(max_length=200)

    def __init__(self, content: str, **kwargs) -> None:
        super().__init__(content=content, **kwargs)


class LiteralQuote(Content, table=False):
    __mapper_args__ = {"polymorphic_identity": ContentType.LiteralQuote}

    type: ContentType = Field(default=ContentType.LiteralQuote)
    author: str = Field(max_length=200)
    literal_type: LiteralType = Field(max_length=20)
    title: str = Field(max_length=200)

    def __init__(self, content: str, **kwargs) -> None:
        super().__init__(content=content, **kwargs)


class Fact(Content, table=False):
    __mapper_args__ = {"polymorphic_identity": ContentType.FACT}

    type: ContentType = Field(default=ContentType.FACT)

    def __init__(self, content: str, **kwargs) -> None:
        super().__init__(content=content, **kwargs)
