import httpx

from app.schema.contents import MemeCandidate

_SUBREDDIT = "catmemes"
_SORT = "top"
_TIME_FILTER = "day"


class RedditClient:
    """비인증 클라이언트"""

    async def fetch_cat_memes(self, count: int) -> list[MemeCandidate]:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://www.reddit.com/r/{_SUBREDDIT}/{_SORT}.json",
                params={"limit": count, "t": _TIME_FILTER},
                headers={"User-Agent": "meow-content/0.1"},
            )
        response.raise_for_status()
        return _parse(response.json())


class RedditOAuthClient:
    """OAuth 클라이언트 — 프로덕션용 (AWS EC2 등 서버 환경)"""

    def __init__(self, client_id: str, client_secret: str, username: str) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._user_agent = f"meow-content/0.1 by /u/{username}"

    async def fetch_cat_memes(self, count: int) -> list[MemeCandidate]:
        token = await self._get_access_token()
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://oauth.reddit.com/r/{_SUBREDDIT}/{_SORT}.json",
                params={"limit": count, "t": _TIME_FILTER},
                headers={
                    "Authorization": f"Bearer {token}",
                    "User-Agent": self._user_agent,
                },
            )
        response.raise_for_status()
        return _parse(response.json())

    async def _get_access_token(self) -> str:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://www.reddit.com/api/v1/access_token",
                data={"grant_type": "client_credentials"},
                auth=(self._client_id, self._client_secret),
                headers={"User-Agent": self._user_agent},
            )
        response.raise_for_status()
        return response.json()["access_token"]


def _parse(data: dict) -> list[MemeCandidate]:
    return [
        MemeCandidate(
            image_url=post["data"]["url"],
            source=f"Reddit-{_SUBREDDIT}",
            author=post["data"]["author"],
        )
        for post in data["data"]["children"]
        if post["data"].get("post_hint") == "image"
    ]


reddit_client = RedditClient()
