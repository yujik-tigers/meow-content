import logging

from playwright.async_api import BrowserContext, async_playwright

from app.enums import ContentType
from app.scrap.base import Scraper
from app.schema.content import NewContent
from app.settings import app_config

logger = logging.getLogger(__name__)

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)
_IMAGE_SUFFIXES = (".jpg", ".jpeg", ".png", ".gif", ".webp")


class RedditMemeScraper(Scraper):

    _SUBREDDIT = "catmemes"

    async def scrape(self) -> list[NewContent]:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
            )
            try:
                context = await browser.new_context(
                    user_agent=_USER_AGENT, locale="en-US"
                )
                try:
                    return await self._fetch_via_json(context)
                except Exception:
                    logger.warning(
                        "reddit top.json fetch failed, falling back to old.reddit HTML",
                        exc_info=True,
                    )
                    return await self._fetch_via_old_reddit(context)
            finally:
                await browser.close()

    async def _fetch_via_json(self, context: BrowserContext) -> list[NewContent]:
        page = await context.new_page()
        response = await page.goto(
            f"https://www.reddit.com/r/{self._SUBREDDIT}/top.json"
            f"?limit={app_config.REDDIT_MEME_COUNT}&t={app_config.REDDIT_TIME_FILTER}",
            wait_until="domcontentloaded",
            timeout=30_000,
        )
        if response is None or response.status != 200:
            status = response.status if response else "no response"
            raise RuntimeError(f"reddit top.json returned {status}")

        data = await response.json()
        return [
            NewContent(
                type=ContentType.REDDIT_MEME,
                image_url=post["data"]["url"],
                author=post["data"]["author"],
                title=post["data"]["title"],
            )
            for post in data["data"]["children"]
            if post["data"].get("post_hint") == "image"
        ]

    async def _fetch_via_old_reddit(self, context: BrowserContext) -> list[NewContent]:
        page = await context.new_page()
        response = await page.goto(
            f"https://old.reddit.com/r/{self._SUBREDDIT}/top/?t={app_config.REDDIT_TIME_FILTER}",
            wait_until="domcontentloaded",
            timeout=30_000,
        )
        if response is None or response.status != 200:
            status = response.status if response else "no response"
            raise RuntimeError(f"old.reddit returned {status}")

        memes: list[NewContent] = []
        for thing in await page.locator("div.thing[data-url]").all():
            image_url = await thing.get_attribute("data-url")
            if not image_url or not image_url.lower().endswith(_IMAGE_SUFFIXES):
                continue
            memes.append(
                NewContent(
                    type=ContentType.REDDIT_MEME,
                    image_url=image_url,
                    author=await thing.get_attribute("data-author"),
                    title=await thing.locator("a.title").first.inner_text(),
                )
            )
            if len(memes) >= app_config.REDDIT_MEME_COUNT:
                break
        return memes


reddit_meme_scraper = RedditMemeScraper()
