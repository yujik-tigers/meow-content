import pytest

from app.enums import ContentStatus, ContentType
from app.exceptions import ContentNotFoundError
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
