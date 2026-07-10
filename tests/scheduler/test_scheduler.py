from contextlib import asynccontextmanager
from datetime import datetime
from unittest.mock import AsyncMock
from zoneinfo import ZoneInfo

import pytest
from pytest_mock import MockerFixture

from app.enums import ContentType
from app.exceptions import NoApprovedContentError
from app.scheduler import _daily_content_job, _weekly_scraping_job
from app.schema.content import Content, NewContent


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


_MEMES = [
    NewContent(
        type=ContentType.REDDIT_MEME,
        image_url="https://i.redd.it/cat.jpg",
        author="user1",
        title="Cat",
    ),
]
_QUOTES = [NewContent(type=ContentType.QUOTE, content="Do or do not", author="Yoda")]


def _patch_scraping(mocker: MockerFixture, mock_repo: AsyncMock) -> None:
    @asynccontextmanager
    async def fake_get_repository():
        yield mock_repo

    mocker.patch("app.scheduler.get_repository", fake_get_repository)


async def test_weekly_scraping_job_inserts_all(mocker: MockerFixture) -> None:
    mock_repo = AsyncMock()
    mock_repo.create_contents.return_value = 1
    _patch_scraping(mocker, mock_repo)

    reddit_client = mocker.patch("app.scheduler.RedditClient").return_value
    reddit_client.fetch_cat_memes = AsyncMock(return_value=_MEMES)
    mocker.patch("app.scheduler.fetch_daily_quotes", AsyncMock(return_value=_QUOTES))

    await _weekly_scraping_job()

    assert mock_repo.create_contents.await_count == 2
    scraped = [call.args[0] for call in mock_repo.create_contents.await_args_list]
    assert scraped == [_MEMES, _QUOTES]


async def test_weekly_scraping_job_isolates_failures(mocker: MockerFixture) -> None:
    mock_repo = AsyncMock()
    mock_repo.create_contents.return_value = 1
    _patch_scraping(mocker, mock_repo)

    reddit_client = mocker.patch("app.scheduler.RedditClient").return_value
    reddit_client.fetch_cat_memes = AsyncMock(side_effect=RuntimeError("blocked"))
    mocker.patch("app.scheduler.fetch_daily_quotes", AsyncMock(return_value=_QUOTES))

    await _weekly_scraping_job()

    mock_repo.create_contents.assert_awaited_once_with(_QUOTES)
