from dataclasses import dataclass
from datetime import date, datetime

from app.content.enums import MemeStatus


@dataclass
class QuoteImagePaths:
    base_image_path: str
    quote_image_path: str
    korean_quote_image_path: str


@dataclass(frozen=True)
class Quote:
    text: str
    speaker: str


@dataclass(frozen=True)
class MemeCandidate:
    image_url: str
    source: str
    author: str


@dataclass(frozen=True)
class MemeAnalysisResult:
    image_url: str
    source: str
    author: str
    meme_text: str
    expressions: str
    translation: str
    background: str | None


@dataclass(frozen=True)
class MemeContent:
    image_url: str
    meme_text: str
    source: str
    author: str
    expressions: str
    translation: str
    background: None | str


@dataclass(frozen=True)
class UpdateMemeStatusRequest:
    status: MemeStatus


@dataclass(frozen=True)
class MemeListItem:
    id: int
    image_url: str
    meme_text: str
    source: str
    author: str
    expressions: str
    translation: str
    background: str | None
    status: MemeStatus
    used_at: date | None
    created_at: datetime
