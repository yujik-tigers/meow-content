from dataclasses import dataclass
from datetime import date, datetime

from app.enums import ContentStatus, ContentType, LiteralType


@dataclass(frozen=True)
class Quote:
    text: str
    speaker: str


@dataclass(frozen=True)
class UpdateContentStatusRequest:
    from_status: ContentStatus
    to_status: ContentStatus

    def __post_init__(self) -> None:
        if self.to_status in (ContentStatus.APPROVED, ContentStatus.REJECTED):
            if self.from_status != ContentStatus.PENDING:
                raise ValueError(
                    f"Cannot transition to {self.to_status} from {self.from_status}: from_status must be PENDING"
                )

        if self.to_status == ContentStatus.USED:
            if self.from_status not in (ContentStatus.APPROVED, ContentStatus.REJECTED):
                raise ValueError(
                    f"Cannot transition to {self.to_status} from {self.from_status}: from_status must be APPROVED or ANALYZED"
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
class ReanalyzeContentField:
    field_name: str
    prompt_guide: str
