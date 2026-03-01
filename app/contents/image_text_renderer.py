import re
from io import BytesIO

from PIL import Image, ImageDraw, ImageFont

from app.contents.quote_creator import Quote
from app.settings import app_config

MAX_LINES = 2
MIN_FONT_SIZE = 20


def _is_korean(text: str) -> bool:
    return bool(re.search(r"[\uAC00-\uD7A3\u3130-\u318F\u1100-\u11FF]", text))


def _wrap_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    max_width: int,
    korean: bool,
) -> list[str]:
    def text_width(s: str) -> int:
        bbox = draw.textbbox((0, 0), s, font=font)
        return int(bbox[2] - bbox[0])

    words = text.split()
    lines = []
    current = ""
    for word in words:
        test = (current + " " + word).strip() if current else word
        if text_width(test) <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def add_quote(image_bytes: bytes, quote: Quote) -> bytes:
    """Overlay meme-style text on the image: all-caps, white fill, black stroke, centered at bottom."""
    img = Image.open(BytesIO(image_bytes)).convert("RGB")
    draw = ImageDraw.Draw(img)
    width, height = img.size

    text = quote.text
    korean = _is_korean(text)
    font_path = app_config.MEME_FONT_PATH_KOR if korean else app_config.MEME_FONT_PATH

    if korean:
        font_size = max(36, width // 18)
    else:
        text = text.upper()
        font_size = max(36, width // 10)

    max_width = int(width * 0.9)

    # Shrink font until text fits within MAX_LINES
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont
    lines: list[str] = []
    while font_size >= MIN_FONT_SIZE:
        try:
            font = ImageFont.truetype(font_path, font_size)
        except Exception:
            font = ImageFont.load_default(size=font_size)
        lines = _wrap_text(draw, text, font, max_width, korean)
        if len(lines) <= MAX_LINES:
            break
        font_size -= 2

    lines = lines[:MAX_LINES]

    speaker_font_size = max(MIN_FONT_SIZE, int(font_size * 0.65))
    try:
        speaker_font = ImageFont.truetype(font_path, speaker_font_size)
    except Exception:
        speaker_font = ImageFont.load_default(size=speaker_font_size)
    speaker_text = f"- {quote.speaker} -"
    speaker_line_spacing = int(speaker_font_size * 1.15)

    line_spacing = int(font_size * 1.15)
    total_text_height = line_spacing * len(lines) + speaker_line_spacing
    margin = int(height * 0.03)
    y = height - total_text_height - margin
    stroke_width = max(2, font_size // 14)

    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        line_width = bbox[2] - bbox[0]
        x = (width - line_width) / 2
        draw.text(
            (x, y),
            line,
            font=font,
            fill="white",
            stroke_width=stroke_width,
            stroke_fill="black",
        )
        y += line_spacing

    speaker_stroke_width = max(1, speaker_font_size // 14)
    speaker_bbox = draw.textbbox((0, 0), speaker_text, font=speaker_font)
    speaker_x = (width - (speaker_bbox[2] - speaker_bbox[0])) / 2
    draw.text(
        (speaker_x, y),
        speaker_text,
        font=speaker_font,
        fill="white",
        stroke_width=speaker_stroke_width,
        stroke_fill="black",
    )

    output = BytesIO()
    img.save(output, format="PNG")
    return output.getvalue()
