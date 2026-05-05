import httpx

from app.schema.contents import MemeCandidate

_SUBREDDIT = "catmemes"
_SORT = "top"
_TIME_FILTER = "day"


class RedditClient:
    async def fetch_cat_memes(self, count: int) -> list[MemeCandidate]:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://www.reddit.com/r/{_SUBREDDIT}/{_SORT}.json",
                params={"limit": count, "t": _TIME_FILTER},
            )
        response.raise_for_status()
        posts = response.json()["data"]["children"]
        return [
            MemeCandidate(
                image_url=post["data"]["url"],
                source=f"Reddit-{_SUBREDDIT}",
                author=post["data"]["author"],
            )
            for post in posts
            if post["data"].get("post_hint") == "image"
        ]


reddit_client = RedditClient()
