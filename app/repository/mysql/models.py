from datetime import date, datetime
from zoneinfo import ZoneInfo

from sqlalchemy import Column, Text
from sqlmodel import Field, SQLModel

from app.content.enums import MemeStatus
from app.schema.contents import MemeContent


class MemeRecord(SQLModel, table=True):
    __tablename__ = "meme_record"  # pyright: ignore[reportAssignmentType]

    id: int | None = Field(default=None, primary_key=True)
    img_url: str = Field(sa_column=Column(Text))
    meme_text: str
    meme_text_translation: str
    author: str = Field(max_length=200)
    source: str = Field(max_length=200)
    expressions: str = Field(max_length=200)
    translation: str = Field(max_length=200)
    background: str = Field(sa_column=Column(Text))
    status: MemeStatus = Field(default=MemeStatus.PENDING, max_length=20)
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
