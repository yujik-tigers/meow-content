import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.dependencies import get_repository
from app.exceptions import NoApprovedContentError
from app.settings import app_config

logger = logging.getLogger(__name__)
_KST = ZoneInfo("Asia/Seoul")


async def _daily_content_job() -> None:
    target_date = datetime.now(_KST).date() + timedelta(days=1)
    logger.info(
        "Running daily content reservation job for %s", target_date.strftime("%y-%m-%d")
    )
    try:
        async with get_repository() as repo:
            content = await repo.reserve_daily_content(target_date)
    except NoApprovedContentError:
        logger.error(
            "No APPROVED content available to reserve for %s",
            target_date.strftime("%y-%m-%d"),
            exc_info=True,
        )
        raise
    logger.info(
        "Reserved content id=%d for %s", content.id, target_date.strftime("%y-%m-%d")
    )


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
    return scheduler
