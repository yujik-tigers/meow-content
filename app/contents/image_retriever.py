import os
from datetime import date

from app.contents.enums import LanguageCode


def get_image_path(language_code: LanguageCode, date: date) -> str:
    return (
        f"{os.getcwd()}/app/images/{date.strftime('%Y%m%d')}_{language_code.value}.png"
    )


def is_exist(language_code: LanguageCode, date: date) -> bool:
    file_path = get_image_path(language_code=language_code, date=date)
    return os.path.exists(file_path)


def retrieve(language_code: LanguageCode, date: date) -> bytes:
    file_path = get_image_path(language_code=language_code, date=date)
    if os.path.exists(file_path):
        with open(file_path, "rb") as f:
            return f.read()
    raise FileNotFoundError("Image not found")


def retrieve_meme_sample(number: int | None = None) -> bytes:
    with open(f"{os.getcwd()}/app/images/meme_example{number or ''}.jpeg", "rb") as f:
        return f.read()
