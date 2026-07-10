import logging
from collections.abc import Awaitable, Callable
from datetime import datetime
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.client.reddit_client import RedditClient
from app.client.zenquotes_client import fetch_daily_quotes
from app.dependencies import get_repository
from app.exceptions import NoApprovedContentError
from app.schema.content import NewContent
from app.settings import app_config

logger = logging.getLogger(__name__)
_KST = ZoneInfo("Asia/Seoul")


async def _daily_content_job() -> None:
    today = datetime.now(_KST).date()
    logger.info(
        "Running daily content reservation job for %s", today.strftime("%y-%m-%d")
    )
    try:
        async with get_repository() as repo:
            content = await repo.reserve_daily_content(today)
    except NoApprovedContentError:
        logger.error(
            "No APPROVED content available to reserve for %s",
            today.strftime("%y-%m-%d"),
            exc_info=True,
        )
        raise
    logger.info("Reserved content id=%d for %s", content.id, today.strftime("%y-%m-%d"))


async def _weekly_scraping_job() -> None:
    scrapers: list[tuple[str, Callable[[], Awaitable[list[NewContent]]]]] = [
        (
            "reddit_meme",
            RedditClient(
                count=app_config.REDDIT_MEME_COUNT,
                time_filter=app_config.REDDIT_TIME_FILTER,
            ).fetch_cat_memes,
        ),
        ("daily_quote", fetch_daily_quotes),
    ]
    for name, scrape in scrapers:
        try:
            contents = await scrape()
            async with get_repository() as repo:
                inserted = await repo.create_contents(contents)
            logger.info(
                "Scraped %d %s contents, inserted %d new", len(contents), name, inserted
            )
        except Exception:
            logger.exception("%s scraping failed; will retry at next scheduled run", name)


def create_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone=_KST)
    scheduler.add_job(
        _daily_content_job,
        CronTrigger(
            hour=app_config.SCHEDULER_HOUR,
            minute=app_config.SCHEDULER_MINUTE,
            timezone=_KST,
        ),
    )
    scheduler.add_job(
        _weekly_scraping_job,
        CronTrigger(
            day_of_week=app_config.SCRAPER_DAY_OF_WEEK,
            hour=app_config.SCRAPER_HOUR,
            minute=app_config.SCRAPER_MINUTE,
            timezone=_KST,
        ),
        misfire_grace_time=3600,
    )
    return scheduler
