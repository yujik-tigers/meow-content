from enum import Enum


class LanguageCode(str, Enum):
    ENGLISH = "eng"
    KOREAN = "kor"
    NONE = "none"

    def to_language_name(self) -> str:
        if self == LanguageCode.ENGLISH:
            return "English"
        if self == LanguageCode.KOREAN:
            return "Korean"
        if self == LanguageCode.NONE:
            return "None"
        raise ValueError(f"Unsupported language code: {self}")


class ImageType(str, Enum):
    QUOTE = "quote"
    MEME = "meme"
