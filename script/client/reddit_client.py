from typing import Literal

import httpx

from script.schema import RedditMemeRaw


class RedditClient:

    _SUBREDDIT = "catmemes"

    async def fetch_cat_memes(
        self, count: int, sort: Literal["top"], time_filter: Literal["day", "week"]
    ) -> list[RedditMemeRaw]:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://www.reddit.com/r/{self._SUBREDDIT}/{sort}.json",
                params={"limit": count, "t": time_filter},
                headers={"User-Agent": "meow-content/0.1"},
            )
        response.raise_for_status()
        return self._parse(response.json())

    def _parse(self, data: dict) -> list[RedditMemeRaw]:
        return [
            RedditMemeRaw(
                image_url=post["data"]["url"],
                author=post["data"]["author"],
                title=post["data"]["title"],
            )
            for post in data["data"]["children"]
            if post["data"].get("post_hint") == "image"
        ]
