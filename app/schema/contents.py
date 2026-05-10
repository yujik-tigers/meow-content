from dataclasses import dataclass
from datetime import date

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
class MemeSaveData:
    img_url: str
    meme_text: str
    meme_text_translation: str
    author: str
    source: str
    expressions: str
    translation: str
    background: str


@dataclass(frozen=True)
class MemeAnalysisResult:
    image_url: str
    source: str
    author: str
    meme_text: str
    expressions: str
    translation: str
    background: str


@dataclass(frozen=True)
class MemeContent:
    image_url: str
    meme_text: str
    meme_text_translation: str
    source: str
    author: str
    expressions: str
    translation: str
    background: str
    status: MemeStatus
    used_at: date | None
    id: int | None = None


@dataclass(frozen=True)
class UpdateMemeBackgroundRequest:
    background: str


@dataclass(frozen=True)
class TriggerScrapingRequest:
    count: int

    def __post_init__(self) -> None:
        if not (1 <= self.count <= 10):
            raise ValueError("count must be between 1 and 10")


@dataclass(frozen=True)
class UpdateMemeStatusRequest:
    status: MemeStatus
