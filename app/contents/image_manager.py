import glob
import os
from datetime import date

from app.contents.enums import ImageType, LanguageCode


def make_image_path_by(
    language_code: LanguageCode,
    date: date,
    image_type: ImageType,
    image_extension: str,
) -> str:
    return f"{os.getcwd()}/app/images/{date.strftime('%Y%m%d')}_{language_code.value}_{image_type.value}.{image_extension}"


def find_image_path_by(
    language_code: LanguageCode,
    date: date,
    image_type: ImageType,
) -> str:
    pattern = f"{os.getcwd()}/app/images/{date.strftime('%Y%m%d')}_{language_code.value}_{image_type.value}.*"
    matches = glob.glob(pattern)
    if not matches:
        raise FileNotFoundError(f"No image found for pattern: {pattern}")
    return matches[0]


def is_exist(
    language_code: LanguageCode,
    date: date,
    image_type: ImageType,
) -> bool:
    try:
        path = find_image_path_by(language_code, date, image_type)
        return path is not None
    except FileNotFoundError:
        return False


def save_image(
    image_bytes: bytes,
    language_code: LanguageCode,
    date: date,
    image_type: ImageType,
    image_extension: str = "png",
) -> str:
    file_path = make_image_path_by(
        language_code=language_code,
        date=date,
        image_type=image_type,
        image_extension=image_extension,
    )
    with open(file_path, "wb") as f:
        f.write(image_bytes)
    return file_path
