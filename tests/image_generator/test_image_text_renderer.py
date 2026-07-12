import pytest
from PIL import Image as PILModule

from app.image_generator import image_text_renderer
from app.image_generator.image_text_renderer import MAX_LINES
from app.settings import app_config

FONT_PATH = app_config.MEME_FONT_PATH
BG_COLOR = (45, 55, 72)  # dark navy — white 텍스트와 대비


@pytest.fixture(autouse=True)
def _patch_font_path(mocker):
    mocker.patch.object(app_config, "MEME_FONT_PATH", FONT_PATH)


@pytest.fixture
def blank_image():
    img = PILModule.new("RGB", (800, 600), color=BG_COLOR)
    img.format = "PNG"
    return img


def test_long_text_fits_within_two_lines(blank_image, mocker):
    """긴 텍스트가 이미지 위에 최대 줄 수(2줄) 이내로 줄바꿈되어 렌더링된다."""
    wrap_spy = mocker.spy(image_text_renderer, "_wrap_text")
    long_text = "The quick brown fox jumps over the lazy dog and then some more words"

    image_text_renderer.add_text(blank_image, long_text)

    assert len(wrap_spy.spy_return) <= MAX_LINES


def test_long_text_with_speaker_fits_within_three_lines(blank_image, mocker):
    """화자가 포함된 긴 텍스트가 본문+화자 합쳐 3줄 이내로 렌더링된다."""
    wrap_spy = mocker.spy(image_text_renderer, "_wrap_text")
    long_text = "The quick brown fox jumps over the lazy dog and then some more words"

    image_text_renderer.add_text(blank_image, long_text, "Aristotle")

    total_lines = len(wrap_spy.spy_return) + 1  # content lines + speaker
    assert total_lines <= MAX_LINES + 1
