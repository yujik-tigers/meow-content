from datetime import date, datetime
from zoneinfo import ZoneInfo

from sqlalchemy import Column, Text
from sqlmodel import Field, SQLModel

from app.content.enums import MemeStatus


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
