from enum import StrEnum


class ContentStatus(StrEnum):
    RAW = "raw"
    ANALYZED = "analyzed"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    USED = "used"


class ImageType(StrEnum):
    QUOTE = "quote"
    MEME = "meme"


class LiteralType(StrEnum):
    MOVIE = "movie"
    BOOK = "book"


class ContentType(StrEnum):
    REDDIT_MEME = "reddit_meme"
    QUOTE = "quote"
    LiteralQuote = "literal_quote"
    FACT = "fact"


class NanoBananaModel(StrEnum):
    NANO_BANANA_2 = "gemini-3.1-flash-image"
    NANO_BANANA_PRO = "gemini-3-pro-image"


class GptImageModel(StrEnum):
    GPT_IMAGE_2 = "gpt-image-2-2026-04-21"


class DayOfWeek(StrEnum):
    MON = "mon"
    TUE = "tue"
    WED = "wed"
    THU = "thu"
    FRI = "fri"
    SAT = "sat"
    SUN = "sun"
