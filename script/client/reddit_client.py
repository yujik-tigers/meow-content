import json
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
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            if e.response.status_code != 403:
                raise
            url = (
                f"https://www.reddit.com/r/{self._SUBREDDIT}/{sort}.json"
                f"?limit={count}&t={time_filter}"
            )
            fallback_path = "script/reddit_fallback.json"
            print("403 에러 발생. 브라우저에서 아래 URL을 열어 JSON을 저장하세요:")
            print(f"  {url}")
            print(f"저장 경로: {fallback_path}")
            input("저장 완료 후 Enter를 누르세요...")
            with open(fallback_path) as f:
                data = json.load(f)
            open(fallback_path, "w").close()
            return self._parse(data)
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
