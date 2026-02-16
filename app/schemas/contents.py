from dataclasses import dataclass
from datetime import date

from app.contents.enums import LanguageCode


@dataclass
class CreateContentRequest:
    created_at: date
    language: LanguageCode = LanguageCode.ENGLISH
