from unittest.mock import AsyncMock, MagicMock, patch

from script.client.zenquotes_client import create_daily_quote


async def test_create_daily_quote_returns_quote():
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = [{"q": "Life is short", "a": "Anonymous"}]

    with patch("script.client.zenquotes_client.httpx.AsyncClient") as mock_cls:
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_cls.return_value)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=None)
        mock_cls.return_value.get = AsyncMock(return_value=mock_response)

        result = await create_daily_quote()

    assert result.text == "Life is short"
    assert result.speaker == "Anonymous"
