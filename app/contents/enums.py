from enum import Enum


class LanguageCode(str, Enum):
    ENGLISH = "eng"
    KOREAN = "kor"

    def to_language_name(self) -> str:
        if self == LanguageCode.ENGLISH:
            return "English"
        if self == LanguageCode.KOREAN:
            return "Korean"
        raise ValueError(f"Unsupported language code: {self}")
