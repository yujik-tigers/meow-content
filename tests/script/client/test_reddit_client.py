from unittest.mock import AsyncMock, MagicMock, patch

from script.client.reddit_client import RedditClient

_MOCK_RESPONSE = {
    "data": {
        "children": [
            {"data": {"url": "https://i.redd.it/cat1.jpg", "author": "user1", "title": "Cat 1", "post_hint": "image"}},
            {"data": {"url": "https://reddit.com/post", "author": "user2", "title": "Link", "post_hint": "link"}},
            {"data": {"url": "https://i.redd.it/cat2.jpg", "author": "user3", "title": "Cat 2", "post_hint": "image"}},
        ]
    }
}


async def test_fetch_cat_memes_returns_only_images(mocker):
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = _MOCK_RESPONSE

    with patch("script.client.reddit_client.httpx.AsyncClient") as mock_cls:
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_cls.return_value)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=None)
        mock_cls.return_value.get = AsyncMock(return_value=mock_response)

        results = await RedditClient().fetch_cat_memes(count=20, sort="top", time_filter="week")

    assert len(results) == 2
    assert results[0].image_url == "https://i.redd.it/cat1.jpg"
    assert results[0].author == "user1"
    assert results[1].image_url == "https://i.redd.it/cat2.jpg"


async def test_fetch_cat_memes_empty_when_no_images(mocker):
    no_images = {"data": {"children": [
        {"data": {"url": "http://link", "author": "u", "title": "t", "post_hint": "link"}},
    ]}}

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = no_images

    with patch("script.client.reddit_client.httpx.AsyncClient") as mock_cls:
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_cls.return_value)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=None)
        mock_cls.return_value.get = AsyncMock(return_value=mock_response)

        results = await RedditClient().fetch_cat_memes(count=10, sort="top", time_filter="day")

    assert results == []
