from typing import override

from script.client.zenquotes_client import create_daily_quotes
from script.schema import DailyQuoteRaw
from script.scrap.base import RawDataScraper


class DailyQuoteScraper(RawDataScraper[DailyQuoteRaw]):

    @override
    async def scrap(self, **kwargs) -> list[DailyQuoteRaw]:
        return await create_daily_quotes()
