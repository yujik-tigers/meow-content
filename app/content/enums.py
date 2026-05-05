from enum import StrEnum


class MemeStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    USED = "used"


class ImageType(StrEnum):
    QUOTE = "quote"
    MEME = "meme"
