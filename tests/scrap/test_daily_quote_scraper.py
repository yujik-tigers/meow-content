from unittest.mock import AsyncMock, MagicMock, patch

from app.enums import ContentType
from app.scrap.daily_quote_scraper import DailyQuoteScraper


async def test_scrape_maps_zenquotes_response_to_new_content() -> None:
    """ZenQuotes API 응답(q/a)이 QUOTE 타입 NewContent 목록으로 매핑된다."""
    mock_response = MagicMock()
    mock_response.json.return_value = [
        {"q": "Life is short", "a": "Anonymous"},
        {"q": "Do or do not", "a": "Yoda"},
    ]

    with patch("app.scrap.daily_quote_scraper.httpx.AsyncClient") as mock_cls:
        mock_cls.return_value.__aenter__.return_value.get = AsyncMock(
            return_value=mock_response
        )
        result = await DailyQuoteScraper().scrape()

    assert len(result) == 2
    assert all(item.type == ContentType.QUOTE for item in result)
    assert result[0].content == "Life is short"
    assert result[0].author == "Anonymous"
