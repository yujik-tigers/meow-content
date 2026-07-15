from unittest.mock import AsyncMock, MagicMock

from pytest_mock import MockerFixture

from app.enums import ContentType
from app.scrap.reddit_meme_scraper import RedditMemeScraper


def _mock_playwright_context(mocker: MockerFixture) -> MagicMock:
    """async_playwright()를 mock하고, browser.new_context()가 반환할 context를 돌려준다."""
    context = MagicMock()
    browser = MagicMock()
    browser.close = AsyncMock()
    browser.new_context = AsyncMock(return_value=context)
    playwright = MagicMock()
    playwright.chromium.launch = AsyncMock(return_value=browser)

    mock_async_playwright = mocker.patch(
        "app.scrap.reddit_meme_scraper.async_playwright"
    )
    mock_async_playwright.return_value.__aenter__.return_value = playwright
    return context


async def test_scrape_via_json_success(mocker: MockerFixture) -> None:
    """top.json 응답 중 이미지 게시물만 REDDIT_MEME NewContent로 변환한다."""
    context = _mock_playwright_context(mocker)
    page = MagicMock()
    context.new_page = AsyncMock(return_value=page)
    response = MagicMock(status=200)
    response.json = AsyncMock(
        return_value={
            "data": {
                "children": [
                    {
                        "data": {
                            "post_hint": "image",
                            "url": "https://i.redd.it/cat.jpg",
                            "author": "user1",
                            "title": "Cat",
                        }
                    },
                    {"data": {"post_hint": "self"}},
                ]
            }
        }
    )
    page.goto = AsyncMock(return_value=response)

    result = await RedditMemeScraper().scrape()

    assert len(result) == 1
    assert result[0].type == ContentType.REDDIT_MEME
    assert result[0].image_url == "https://i.redd.it/cat.jpg"
    assert result[0].author == "user1"
    assert result[0].title == "Cat"


async def test_scrape_falls_back_to_old_reddit_on_json_failure(
    mocker: MockerFixture,
) -> None:
    """top.json 조회가 실패하면 old.reddit HTML 파싱으로 폴백한다."""
    context = _mock_playwright_context(mocker)
    json_page = MagicMock()
    html_page = MagicMock()
    context.new_page = AsyncMock(side_effect=[json_page, html_page])
    json_page.goto = AsyncMock(return_value=MagicMock(status=403))

    thing = MagicMock()
    thing.get_attribute = AsyncMock(side_effect=["https://i.redd.it/cat2.jpg", "user2"])
    title_locator = MagicMock()
    title_locator.first.inner_text = AsyncMock(return_value="Cat 2")
    thing.locator.return_value = title_locator
    html_page.goto = AsyncMock(return_value=MagicMock(status=200))
    html_page.locator.return_value.all = AsyncMock(return_value=[thing])

    result = await RedditMemeScraper().scrape()

    assert len(result) == 1
    assert result[0].type == ContentType.REDDIT_MEME
    assert result[0].image_url == "https://i.redd.it/cat2.jpg"
    assert result[0].author == "user2"
    assert result[0].title == "Cat 2"
