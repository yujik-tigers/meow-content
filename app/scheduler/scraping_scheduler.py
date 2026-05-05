import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.client.reddit_client import reddit_client
from app.content import meme_analyzer
from app.db.engine import AsyncSessionLocal
from app.db.repository import MemeRepository

logger = logging.getLogger(__name__)


class ScrapingScheduler:
    def __init__(self) -> None:
        self._scheduler = AsyncIOScheduler()
        self._scheduler.add_job(
            self._scrape_and_analyze,
            CronTrigger(hour=23, timezone="America/New_York"),
        )

    def start(self) -> None:
        self._scheduler.start()
        logger.info("Scraping scheduler started (runs daily at 23:00 ET)")

    def stop(self) -> None:
        self._scheduler.shutdown(wait=False)

    async def _scrape_and_analyze(self, count: int = 3) -> None:
        logger.info("Reddit cat meme scraping job started")
        try:
            candidates = await reddit_client.fetch_cat_memes(count)
        except Exception as e:
            logger.error(f"Failed to fetch memes from Reddit: {e}")
            return

        async with AsyncSessionLocal() as session:
            repository = MemeRepository(session)
            for candidate in candidates:
                try:
                    result = await meme_analyzer.analyze_meme(candidate.image_url)
                    meme_id = await repository.save(candidate, result)
                    logger.info(f"Saved meme id={meme_id} from {candidate.source}")
                except Exception as e:
                    logger.error(f"Failed to process meme {candidate.image_url}: {e}")

        logger.info(f"Scraping job done — processed {len(candidates)} candidates")


scraping_scheduler = ScrapingScheduler()
