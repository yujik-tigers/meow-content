from enum import StrEnum


class MemeStatus(StrEnum):
    RAW = "raw"
    ANALYZED = "analyzed"
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
