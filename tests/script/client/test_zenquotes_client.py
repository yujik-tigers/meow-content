from unittest.mock import AsyncMock, MagicMock, patch

from script.client.zenquotes_client import create_daily_quotes
from script.schema import DailyQuoteRaw


async def test_create_daily_quotes():
    mock_response = MagicMock()
    mock_response.json.return_value = [
        {"q": "Life is short", "a": "Anonymous"},
        {"q": "Do or do not", "a": "Yoda"},
    ]

    with patch("script.client.zenquotes_client.httpx.AsyncClient") as mock_cls:
        mock_cls.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
        result = await create_daily_quotes()

    assert len(result) == 2
    assert all(isinstance(item, DailyQuoteRaw) for item in result)
    assert result[0].quote == "Life is short"
    assert result[0].author == "Anonymous"
