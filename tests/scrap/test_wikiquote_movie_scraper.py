from unittest.mock import AsyncMock, MagicMock, patch

from app.enums import ContentType, LiteralType
from app.scrap.wikiquote_movie_scraper import (
    WikiquoteMovieScraper,
    _dialogue_index,
    _extract_quote_candidates,
    _parse_speaker_bullet,
    _sections,
    _strip_emphasis,
    _strip_refs_and_links,
)

_FILM_WIKITEXT = """
==Rick==
* Here's looking at you, kid, this line is definitely long enough.
==Others==
* A plain catch-all line that has no inline speaker tag at all.
==Quotes from Holmes Literature==
* '''Sam''': Play it once, Sam, for old times' sake, if you please.
==Dialogue==
:'''Rick''': Hello, Louis, this dialogue line should never be used as a quote.
==Cast==
* Humphrey Bogart as Rick
==Taglines==
* Some tagline that should never appear in the output.
"""


def _mock_response(payload: dict) -> MagicMock:
    response = MagicMock()
    response.json.return_value = payload
    response.raise_for_status = MagicMock()
    return response


async def test_scrape_happy_path(mocker) -> None:
    """큐레이션된 인기 영화 목록에서 고른 영화 페이지를 파싱해 Dialogue 이전 캐릭터 헤딩의 대사만 LiteralQuote NewContent로 만든다."""
    mocker.patch(
        "app.scrap.wikiquote_movie_scraper.random.choice",
        return_value="Casablanca",
    )

    with patch("app.scrap.wikiquote_movie_scraper.httpx.AsyncClient") as mock_cls:
        mock_cls.return_value.__aenter__.return_value.get = AsyncMock(
            return_value=_mock_response({"parse": {"wikitext": _FILM_WIKITEXT}})
        )
        result = await WikiquoteMovieScraper().scrape()

    assert len(result) == 1
    item = result[0]
    assert item.type == ContentType.LiteralQuote
    assert item.literal_type == LiteralType.MOVIE
    assert item.title == "Casablanca"
    assert item.content == "Here's looking at you, kid, this line is definitely long enough."
    assert item.author == "Rick"


async def test_scrape_returns_empty_when_film_page_errors() -> None:
    """선택된 영화 페이지 조회가 MediaWiki 'error'를 반환하면 빈 리스트를 반환한다."""
    with patch("app.scrap.wikiquote_movie_scraper.httpx.AsyncClient") as mock_cls:
        mock_cls.return_value.__aenter__.return_value.get = AsyncMock(
            return_value=_mock_response({"error": {"code": "missingtitle"}})
        )
        result = await WikiquoteMovieScraper().scrape()

    assert result == []


async def test_scrape_returns_empty_when_film_page_has_no_dialogue_section() -> None:
    """선택된 영화 페이지에 Dialogue 섹션(경계 기준)이 없으면 빈 리스트를 반환한다."""
    no_dialogue_wikitext = "==Cast==\n* Someone\n==Taglines==\n* A tagline\n"

    with patch("app.scrap.wikiquote_movie_scraper.httpx.AsyncClient") as mock_cls:
        mock_cls.return_value.__aenter__.return_value.get = AsyncMock(
            return_value=_mock_response({"parse": {"wikitext": no_dialogue_wikitext}})
        )
        result = await WikiquoteMovieScraper().scrape()

    assert result == []


def test_dialogue_index_locates_heading_case_insensitively() -> None:
    """헤딩 이름이 대소문자와 무관하게 'dialogue'와 일치하는 섹션의 인덱스를 찾는다."""
    sections = _sections("==Rick==\n* line\n==DIALOGUE==\n* line two\n==Cast==\n* x\n")
    assert _dialogue_index(sections) == 1


def test_dialogue_index_returns_none_when_absent() -> None:
    """Dialogue 섹션이 없으면 None을 반환한다."""
    sections = _sections("==Cast==\n* Someone\n")
    assert _dialogue_index(sections) is None


def test_extract_quote_candidates_uses_only_sections_before_dialogue() -> None:
    """Dialogue 이전의 캐릭터 헤딩만 후보로 남고, catch-all 섹션과 Dialogue 이후 섹션은 전부 제외된다."""
    candidates = _extract_quote_candidates(_FILM_WIKITEXT)

    assert candidates == [
        ("Rick", "Here's looking at you, kid, this line is definitely long enough.")
    ]


def test_extract_quote_candidates_returns_empty_without_dialogue_heading() -> None:
    """Dialogue 헤딩이 없는 페이지는 경계를 잡을 수 없으므로 빈 리스트를 반환한다."""
    wikitext = "==Rick==\n* Here's looking at you, kid, this line is long enough.\n"
    assert _extract_quote_candidates(wikitext) == []


def test_extract_quote_candidates_excludes_named_catch_all_heading() -> None:
    """_EXCLUDED_HEADINGS에 등록된 헤딩(예: Others)은 화자 표기가 없어도 이름만으로 제외된다."""
    wikitext = (
        "==Others==\n"
        "* A plain catch-all line with no inline speaker tag at all here.\n"
        "==Dialogue==\n"
        "* placeholder\n"
    )
    assert _extract_quote_candidates(wikitext) == []


def test_extract_quote_candidates_excludes_unlisted_mixed_speaker_heading() -> None:
    """exclude-list에 없는 헤딩도 화자 표기가 섞여 있으면 구조적으로 제외된다."""
    wikitext = (
        "==Quotes from Holmes Literature==\n"
        "* '''Sam''': Play it once, Sam, for old times' sake, if you please.\n"
        "==Dialogue==\n"
        "* placeholder\n"
    )
    assert _extract_quote_candidates(wikitext) == []


def test_strip_refs_and_links_resolves_links_and_removes_refs() -> None:
    """[[a|b]]는 표시 텍스트로, <ref>...</ref>는 제거한다."""
    raw = "See [[Page|Display]] and <ref>cite</ref> tail"
    assert _strip_refs_and_links(raw) == "See Display and  tail"


def test_strip_emphasis_removes_bold_and_italic_markers() -> None:
    """'''볼드'''와 ''이탤릭'' 마크업을 제거한다."""
    assert _strip_emphasis("'''Bold''' and ''italic''") == "Bold and italic"


def test_parse_speaker_bullet_detects_speaker_prefix() -> None:
    """'''화자''': 텍스트 형태의 불릿에서 화자와 대사를 분리한다."""
    assert _parse_speaker_bullet("'''Renault''': Hello, Rick.") == (
        "Renault",
        "Hello, Rick.",
    )


def test_parse_speaker_bullet_returns_none_without_speaker() -> None:
    """화자 표기가 없는 불릿은 None을 반환한다."""
    assert _parse_speaker_bullet("Just a plain quote line.") is None
