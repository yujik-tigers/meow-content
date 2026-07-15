from contextlib import asynccontextmanager
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from pytest_mock import MockerFixture
from sqlmodel import select

from app.enums import ContentStatus, ContentType
from app.exceptions import NoApprovedContentError
from app.repository.mysql._models import ContentRecord
from app.repository.mysql.repository import MySQLContentRepository
from app.scheduler import _daily_content_job


@pytest.fixture
def patch_get_repository(mocker: MockerFixture, db_session_factory) -> None:
    """스케줄러의 get_repository가 롤백 격리된 실제 repo를 사용하도록 교체한다."""

    @asynccontextmanager
    async def _fake():
        session = db_session_factory()
        try:
            yield MySQLContentRepository(session)
        finally:
            await session.close()

    mocker.patch("app.scheduler.get_repository", _fake)


async def _seed_approved_contents(db_session) -> None:
    db_session.add_all(
        [
            ContentRecord(
                type=ContentType.QUOTE,
                status=ContentStatus.APPROVED,
                content="Do or do not",
            ),
            ContentRecord(
                type=ContentType.REDDIT_MEME,
                status=ContentStatus.APPROVED,
                image_url="https://i.redd.it/cat.jpg",
            ),
        ]
    )
    await db_session.commit()


async def test_daily_content_job_success(patch_get_repository, db_session) -> None:
    """일일 잡이 승인된 콘텐츠 하나를 오늘 날짜(KST)로 예약(USED) 처리한다."""
    await _seed_approved_contents(db_session)

    await _daily_content_job()

    used = (
        await db_session.exec(
            select(ContentRecord).where(ContentRecord.status == ContentStatus.USED)
        )
    ).all()
    assert len(used) == 1
    assert used[0].used_at == datetime.now(ZoneInfo("Asia/Seoul")).date()


async def test_daily_content_job_no_approved_raises(patch_get_repository) -> None:
    """예약할 승인 콘텐츠가 없으면 NoApprovedContentError를 전파한다."""
    with pytest.raises(NoApprovedContentError):
        await _daily_content_job()
