from typing import override

from script.client.reddit_client import RedditClient
from script.schema import RedditMemeRaw
from script.scrap.base import RawDataScraper


class RedditMemeScraper(RawDataScraper[RedditMemeRaw]):

    def __init__(self) -> None:
        self._client = RedditClient()

    @override
    async def scrap(self, **kwargs) -> list[RedditMemeRaw]:
        count = kwargs.get("count", 20)
        sort = kwargs.get("sort", "top")
        time_filter = kwargs.get("time_filter", "week")

        return await self._client.fetch_cat_memes(
            count=count, sort=sort, time_filter=time_filter
        )
