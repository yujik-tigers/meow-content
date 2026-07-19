from dataclasses import dataclass
from datetime import date, datetime

from app.enums import (
    ContentStatus,
    ContentType,
    GptImageModel,
    LiteralType,
    NanoBananaModel,
    RegenerateType,
)


@dataclass(frozen=True)
class UpdateContentStatusRequest:
    from_status: ContentStatus
    to_status: ContentStatus

    def __post_init__(self) -> None:
        if self.to_status == ContentStatus.APPROVED:
            if self.from_status != ContentStatus.PENDING:
                raise ValueError(
                    f"Cannot transition to {self.to_status} from {self.from_status}: from_status must be PENDING"
                )

        if self.to_status == ContentStatus.USED:
            raise ValueError(
                f"Cannot transition to {self.to_status} using API request, It only can be changed by scheduler"
            )


@dataclass(frozen=True, kw_only=True)
class Content:
    id: int
    type: ContentType
    status: ContentStatus
    content: str | None = None
    content_translation: str | None = None
    expression: str | None = None
    expression_translation: str | None = None
    background: str | None = None
    created_at: datetime
    used_at: date | None = None
    image_url: str | None = None
    author: str | None = None
    title: str | None = None
    literal_type: LiteralType | None = None


@dataclass(frozen=True, kw_only=True)
class NewContent:
    type: ContentType
    content: str | None = None
    image_url: str | None = None
    author: str | None = None
    title: str | None = None
    literal_type: LiteralType | None = None


@dataclass(frozen=True, kw_only=True)
class ReanalyzeContentField:
    field_name: str
    prompt_guide: str


@dataclass(frozen=True, kw_only=True)
class GenerateImageRequest:
    model: GptImageModel | NanoBananaModel
    content_type: ContentType


@dataclass(frozen=True, kw_only=True)
class RegenerateImageRequest:
    prompt: str
    regenerate_type: RegenerateType
    content_type: ContentType
    model: GptImageModel | NanoBananaModel


@dataclass(frozen=True, kw_only=True)
class ScrapingRequest:
    content_type: ContentType
