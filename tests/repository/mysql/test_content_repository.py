from datetime import date

import pytest

from app.enums import ContentStatus, ContentType, LiteralType
from app.exceptions import ContentNotFoundError, NoApprovedContentError
from app.repository.mysql.repository import MySQLContentRepository
from app.schema.content import NewContent


@pytest.fixture
def content_repository(db_session) -> MySQLContentRepository:
    return MySQLContentRepository(db_session)


async def test_create_contents_adds_and_commits(content_repository) -> None:
    """새 콘텐츠 목록을 저장하면 저장 건수를 반환하고 실제 행이 생성된다."""
    inserted = await content_repository.create_contents(
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
    memes = await content_repository.fetch_contents_by(
        ContentStatus.RAW, ContentType.REDDIT_MEME, 0, 10
    )
    assert len(memes) == 1
    assert memes[0].image_url == "https://i.redd.it/cat.jpg"
    quotes = await content_repository.fetch_contents_by(
        ContentStatus.RAW, ContentType.QUOTE, 0, 10
    )
    assert len(quotes) == 1
    assert quotes[0].content == "Do or do not"


async def test_create_contents_skips_duplicates(content_repository) -> None:
    """이미 저장된 image_url·명언 텍스트와 중복되는 콘텐츠는 저장에서 제외된다."""
    await content_repository.create_contents(
        [
            NewContent(
                type=ContentType.REDDIT_MEME,
                image_url="https://i.redd.it/dup.jpg",
                author="user1",
                title="Dup",
            ),
            NewContent(type=ContentType.QUOTE, content="Known quote", author="A"),
        ]
    )

    inserted = await content_repository.create_contents(
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
        ]
    )

    assert inserted == 2
    memes = await content_repository.fetch_contents_by(
        ContentStatus.RAW, ContentType.REDDIT_MEME, 0, 10
    )
    assert {c.image_url for c in memes} == {
        "https://i.redd.it/dup.jpg",
        "https://i.redd.it/new.jpg",
    }
    quotes = await content_repository.fetch_contents_by(
        ContentStatus.RAW, ContentType.QUOTE, 0, 10
    )
    assert {c.content for c in quotes} == {"Known quote", "Fresh quote"}


async def test_create_contents_truncates_long_fields(content_repository) -> None:
    """author·title이 컬럼 최대 길이(200자)를 넘으면 잘라서 저장한다."""
    await content_repository.create_contents(
        [
            NewContent(
                type=ContentType.REDDIT_MEME,
                image_url="https://i.redd.it/cat.jpg",
                author="a" * 300,
                title="t" * 300,
            ),
        ]
    )

    memes = await content_repository.fetch_contents_by(
        ContentStatus.RAW, ContentType.REDDIT_MEME, 0, 10
    )
    assert len(memes[0].author) == 200
    assert len(memes[0].title) == 200


async def test_update_status_rolls_back_for_missing_content(content_repository) -> None:
    """존재하지 않는 콘텐츠 상태 변경은 롤백되고 세션은 계속 사용할 수 있다."""
    with pytest.raises(ContentNotFoundError):
        await content_repository.update_status(99999, ContentStatus.APPROVED)

    contents = await content_repository.fetch_contents_by(
        ContentStatus.RAW, ContentType.QUOTE, 0, 10
    )
    assert contents == []


async def test_create_contents_persists_literal_type(content_repository) -> None:
    """literal_quote 콘텐츠는 literal_type이 함께 저장·조회된다."""
    await content_repository.create_contents(
        [
            NewContent(
                type=ContentType.LiteralQuote,
                content="Here's looking at you, kid.",
                author="Rick",
                title="Casablanca",
                literal_type=LiteralType.MOVIE,
            ),
        ]
    )

    literal_quotes = await content_repository.fetch_contents_by(
        ContentStatus.RAW, ContentType.LiteralQuote, 0, 10
    )
    assert len(literal_quotes) == 1
    assert literal_quotes[0].title == "Casablanca"
    assert literal_quotes[0].literal_type == LiteralType.MOVIE


async def test_create_contents_dedups_literal_quote_by_text(content_repository) -> None:
    """literal_quote도 quote와 마찬가지로 동일 텍스트가 중복 저장되지 않는다."""
    await content_repository.create_contents(
        [
            NewContent(
                type=ContentType.LiteralQuote,
                content="Known movie quote",
                author="Rick",
                title="Casablanca",
                literal_type=LiteralType.MOVIE,
            ),
        ]
    )

    inserted = await content_repository.create_contents(
        [
            NewContent(
                type=ContentType.LiteralQuote,
                content="Known movie quote",
                author="Rick",
                title="Casablanca",
                literal_type=LiteralType.MOVIE,
            ),
            NewContent(
                type=ContentType.LiteralQuote,
                content="Fresh movie quote",
                author="Ilsa",
                title="Casablanca",
                literal_type=LiteralType.MOVIE,
            ),
        ]
    )

    assert inserted == 1
    literal_quotes = await content_repository.fetch_contents_by(
        ContentStatus.RAW, ContentType.LiteralQuote, 0, 10
    )
    assert {c.content for c in literal_quotes} == {
        "Known movie quote",
        "Fresh movie quote",
    }


async def test_create_contents_dedups_fact_by_text(content_repository) -> None:
    """fact도 quote와 마찬가지로 동일 텍스트가 중복 저장되지 않는다."""
    await content_repository.create_contents(
        [
            NewContent(type=ContentType.FACT, content="Known cat fact"),
        ]
    )

    inserted = await content_repository.create_contents(
        [
            NewContent(type=ContentType.FACT, content="Known cat fact"),
            NewContent(type=ContentType.FACT, content="Fresh cat fact"),
        ]
    )

    assert inserted == 1
    facts = await content_repository.fetch_contents_by(
        ContentStatus.RAW, ContentType.FACT, 0, 10
    )
    assert {c.content for c in facts} == {"Known cat fact", "Fresh cat fact"}


async def test_reserve_daily_content_rotates_across_four_types(
    content_repository,
) -> None:
    """day % 4 로테이션에 맞춰 reddit_meme/quote/literal_quote/fact를 순서대로 예약한다."""
    await content_repository.create_contents(
        [
            NewContent(
                type=ContentType.REDDIT_MEME,
                image_url="https://i.redd.it/rotation.jpg",
                author="user1",
                title="Cat",
            ),
            NewContent(type=ContentType.QUOTE, content="Rotation quote", author="A"),
            NewContent(
                type=ContentType.LiteralQuote,
                content="Rotation movie quote",
                author="Rick",
                title="Casablanca",
                literal_type=LiteralType.MOVIE,
            ),
            NewContent(type=ContentType.FACT, content="Rotation cat fact"),
        ]
    )
    for content_type in (
        ContentType.REDDIT_MEME,
        ContentType.QUOTE,
        ContentType.LiteralQuote,
        ContentType.FACT,
    ):
        raw = await content_repository.fetch_contents_by(
            ContentStatus.RAW, content_type, 0, 10
        )
        await content_repository.update_status(raw[0].id, ContentStatus.APPROVED)

    reddit_meme_day = await content_repository.reserve_daily_content(date(2026, 7, 4))
    assert reddit_meme_day.type == ContentType.REDDIT_MEME

    quote_day = await content_repository.reserve_daily_content(date(2026, 7, 5))
    assert quote_day.type == ContentType.QUOTE

    literal_quote_day = await content_repository.reserve_daily_content(
        date(2026, 7, 6)
    )
    assert literal_quote_day.type == ContentType.LiteralQuote

    fact_day = await content_repository.reserve_daily_content(date(2026, 7, 7))
    assert fact_day.type == ContentType.FACT


async def test_reserve_daily_content_raises_when_bucket_has_no_approved_content(
    content_repository,
) -> None:
    """해당 요일 버킷의 타입에 APPROVED 콘텐츠가 없으면 예외가 발생한다."""
    with pytest.raises(NoApprovedContentError):
        await content_repository.reserve_daily_content(date(2026, 7, 3))
