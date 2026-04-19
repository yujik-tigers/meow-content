from dataclasses import dataclass
from datetime import date


@dataclass
class CreateContentRequest:
    created_at: date


@dataclass
class QuoteImagePaths:
    base_image_path: str
    quote_image_path: str
    korean_quote_image_path: str


@dataclass(frozen=True)
class Quote:
    text: str
    speaker: str
