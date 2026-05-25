from contextlib import asynccontextmanager
from datetime import datetime
from unittest.mock import AsyncMock
from zoneinfo import ZoneInfo

import pytest
from pytest_mock import MockerFixture

from app.exceptions import NoApprovedContentError
from app.scheduler import _daily_content_job
from app.schema.content import Content


async def test_daily_content_job_success(mocker: MockerFixture, make_content) -> None:
    content: Content = make_content(id=42)
    mock_repo = AsyncMock()
    mock_repo.reserve_daily_content.return_value = content

    @asynccontextmanager
    async def fake_get_repository():
        yield mock_repo

    mocker.patch("app.scheduler.get_repository", fake_get_repository)

    await _daily_content_job()

    mock_repo.reserve_daily_content.assert_called_once()
    call_args = mock_repo.reserve_daily_content.call_args[0]
    assert call_args[0] == datetime.now(ZoneInfo("Asia/Seoul")).date()


async def test_daily_content_job_no_approved_raises(mocker: MockerFixture) -> None:
    mock_repo = AsyncMock()
    mock_repo.reserve_daily_content.side_effect = NoApprovedContentError()

    @asynccontextmanager
    async def fake_get_repository():
        yield mock_repo

    mocker.patch("app.scheduler.get_repository", fake_get_repository)

    with pytest.raises(NoApprovedContentError):
        await _daily_content_job()
