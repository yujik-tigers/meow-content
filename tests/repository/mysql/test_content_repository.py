from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from app.enums import ContentType
from app.repository.mysql.repository import MySQLContentRepository
from app.schema.content import NewContent


def _make_session(existing_urls: list[str], existing_quotes: list[str]) -> AsyncMock:
    session = AsyncMock()
    session.add_all = MagicMock()
    results = [
        SimpleNamespace(all=lambda: existing_urls),
        SimpleNamespace(all=lambda: existing_quotes),
    ]
    session.exec.side_effect = results
    return session


async def test_create_contents_adds_and_commits() -> None:
    session = _make_session([], [])
    repository = MySQLContentRepository(session)

    inserted = await repository.create_contents(
        [
            NewContent(
                type=ContentType.REDDIT_MEME,
                image_url="https://i.redd.it/cat.jpg",
                author="user1",
                title="Cat",
            ),
            NewContent(type=ContentType.QUOTE, content="Do or do not", author="Yoda"),
        ]
    )

    assert inserted == 2
    session.add_all.assert_called_once()
    added = session.add_all.call_args.args[0]
    assert added[0].type == ContentType.REDDIT_MEME
    assert added[0].image_url == "https://i.redd.it/cat.jpg"
    assert added[1].type == ContentType.QUOTE
    assert added[1].content == "Do or do not"
    session.commit.assert_awaited_once()


async def test_create_contents_skips_duplicates() -> None:
    session = _make_session(["https://i.redd.it/dup.jpg"], ["Known quote"])
    repository = MySQLContentRepository(session)

    inserted = await repository.create_contents(
        [
            NewContent(
                type=ContentType.REDDIT_MEME,
                image_url="https://i.redd.it/dup.jpg",
                author="user1",
                title="Dup",
            ),
            NewContent(
                type=ContentType.REDDIT_MEME,
                image_url="https://i.redd.it/new.jpg",
                author="user2",
                title="New",
            ),
            NewContent(type=ContentType.QUOTE, content="Known quote", author="A"),
            NewContent(type=ContentType.QUOTE, content="Fresh quote", author="B"),
            NewContent(type=ContentType.QUOTE, content="Fresh quote", author="B"),
        ]
    )

    assert inserted == 2
    added = session.add_all.call_args.args[0]
    assert [record.image_url for record in added] == ["https://i.redd.it/new.jpg", None]
    assert added[1].content == "Fresh quote"


async def test_create_contents_truncates_long_fields() -> None:
    session = _make_session([], [])
    repository = MySQLContentRepository(session)

    await repository.create_contents(
        [
            NewContent(
                type=ContentType.REDDIT_MEME,
                image_url="https://i.redd.it/cat.jpg",
                author="a" * 300,
                title="t" * 300,
            ),
        ]
    )

    added = session.add_all.call_args.args[0]
    assert len(added[0].author) == 200
    assert len(added[0].title) == 200


async def test_create_contents_rolls_back_on_error() -> None:
    session = _make_session([], [])
    session.commit.side_effect = RuntimeError("boom")
    repository = MySQLContentRepository(session)

    try:
        await repository.create_contents(
            [NewContent(type=ContentType.QUOTE, content="q", author="a")]
        )
    except RuntimeError:
        pass

    session.rollback.assert_awaited_once()
