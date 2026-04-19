import os
from datetime import date

from app.contents.enums import ImageType, LanguageCode


def get_image_path(
    language_code: LanguageCode, date: date, image_type: ImageType
) -> str:
    return f"{os.getcwd()}/app/images/{date.strftime('%Y%m%d')}_{language_code.value}_{image_type.value}.png"


def is_exist(language_code: LanguageCode, date: date, image_type: ImageType) -> bool:
    file_path = get_image_path(language_code, date, image_type)
    return os.path.exists(file_path)


def retrieve(language_code: LanguageCode, date: date, image_type: ImageType) -> bytes:
    if is_exist(language_code, date, image_type):
        with open(
            get_image_path(language_code, date, image_type),
            "rb",
        ) as f:
            return f.read()

    raise FileNotFoundError("Image not found")
