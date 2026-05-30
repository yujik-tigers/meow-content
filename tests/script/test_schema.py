from dataclasses import FrozenInstanceError

import pytest

from app.enums import ContentType
from app.repository.mysql._models import ContentRecord
from script.schema import DailyQuoteRaw, RedditMemeRaw


def test_reddit_meme_raw_to_entity():
    raw = RedditMemeRaw(image_url="https://i.redd.it/cat.jpg", author="u/catposter", title="My cat doing a thing")
    entity = raw.to_entity()

    assert isinstance(entity, ContentRecord)
    assert entity.type == ContentType.REDDIT_MEME
    assert entity.image_url == raw.image_url
    assert entity.author == raw.author
    assert entity.title == raw.title

    with pytest.raises(FrozenInstanceError):
        raw.image_url = "https://other.jpg"  # type: ignore[misc]


def test_daily_quote_raw_to_entity():
    raw = DailyQuoteRaw(quote="The only way to do great work is to love what you do.", author="Steve Jobs")
    entity = raw.to_entity()

    assert isinstance(entity, ContentRecord)
    assert entity.type == ContentType.QUOTE
    assert entity.content == raw.quote
    assert entity.author == raw.author

    with pytest.raises(FrozenInstanceError):
        raw.quote = "other"  # type: ignore[misc]
