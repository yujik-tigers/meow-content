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
