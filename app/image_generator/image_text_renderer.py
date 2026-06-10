import logging
from io import BytesIO

from PIL import ImageDraw, ImageFont
from PIL.Image import Image

from app.settings import app_config

MAX_LINES = 2
MIN_FONT_SIZE = 20


logger = logging.getLogger(__name__)


def add_text(image: Image, text: str, speaker: str | None = None) -> Image:
    img = image.convert("RGB")
    draw = ImageDraw.Draw(img)
    width, height = img.size

    font_path = app_config.MEME_FONT_PATH

    font_size = max(36, width // 10)

    max_width = int(width * 0.9)

    # Shrink font until text fits within MAX_LINES
    font = ImageFont.truetype(font_path, font_size)
    lines = []
    while font_size >= MIN_FONT_SIZE:
        lines = _wrap_text(draw, text, font, max_width)
        if len(lines) <= MAX_LINES:
            break
        font_size -= 2
        font = ImageFont.truetype(font_path, font_size)

    line_spacing = int(font_size * 1.15)
    speaker_font_size = max(MIN_FONT_SIZE, int(font_size * 0.65)) if speaker else 0
    speaker_line_spacing = int(speaker_font_size * 1.15)

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

    if speaker:
        speaker_font = ImageFont.truetype(font_path, speaker_font_size)
        speaker_text = f"- {speaker} -"
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
    img.save(output, format=image.format)
    return img


def _wrap_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    max_width: int,
) -> list[str]:
    def text_width(s: str) -> int:
        bbox = draw.textbbox((0, 0), s, font=font)
        return int(bbox[2] - bbox[0])

    words = text.split()
    lines = []
    current = ""
    for word in words:
        test = (current + " " + word).strip()
        if text_width(test) <= max_width:
            current = test
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines
