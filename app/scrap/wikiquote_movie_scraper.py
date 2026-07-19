import logging
import random
import re

import httpx

from app.enums import ContentType, LiteralType
from app.schema.content import NewContent
from app.scrap.base import Scraper

logger = logging.getLogger(__name__)

_API_URL = "https://en.wikiquote.org/w/api.php"
_USER_AGENT = "meow-content-bot/1.0 (contact: ghkdgus28@gmail.com)"
_MAIN_LIST_PAGE = "List of films"
_MAX_QUOTES_PER_FILM = 5

_SUBPAGE_TITLE_RE = re.compile(r"List of films \([^)]+\)")
_FILM_LINK_RE = re.compile(r"^\*(?!\*)\s*.*?\[\[([^\]|]+)", re.MULTILINE)
_SECTION_RE = re.compile(r"^==([^=\n].*?)==[ \t]*$", re.MULTILINE)
_BULLET_RE = re.compile(r"^[*:](?!\*|:)\s*(.+)$", re.MULTILINE)
_SPEAKER_RE = re.compile(r"^'''(?P<speaker>[^']+)'''\s*:\s*(?P<line>.+)$")
_REF_RE = re.compile(r"<ref[^>]*/?>.*?(</ref>|$)", re.DOTALL)
_SELF_CLOSING_REF_RE = re.compile(r"<ref[^>]*/>")
_LINK_RE = re.compile(r"\[\[(?:[^\]|]*\|)?([^\]]+)\]\]")
_LEADING_BRACKET_RE = re.compile(r"^\[[^\]]*\]\s*")
_SENTENCE_SPLIT_RE = re.compile(r"[.!?]+")

_DIALOGUE_HEADING = "dialogue"
# Known catch-all headings that appear before "Dialogue" but aren't a single
# character's curated quotes. Most such sections are already caught structurally
# (see _extract_quote_candidates), but add exceptions here as they're found.
_EXCLUDED_HEADINGS = {"others"}


def _strip_refs_and_links(text: str) -> str:
    text = _REF_RE.sub("", text)
    text = _SELF_CLOSING_REF_RE.sub("", text)
    text = _LINK_RE.sub(r"\1", text)
    return text


def _strip_emphasis(text: str) -> str:
    text = text.replace("'''", "").replace("''", "")
    text = _LEADING_BRACKET_RE.sub("", text)
    return text.strip()


def _parse_speaker_bullet(raw: str) -> tuple[str, str] | None:
    # Speaker detection must run before bold-marker stripping, since it matches on
    # the literal '''Speaker''' markers that _strip_emphasis would otherwise remove.
    structural = _strip_refs_and_links(raw)
    match = _SPEAKER_RE.match(structural)
    if not match:
        return None
    return _strip_emphasis(match.group("speaker")), _strip_emphasis(match.group("line"))


def _sentence_count(text: str) -> int:
    return len([s for s in _SENTENCE_SPLIT_RE.split(text) if s.strip()])


def _sections(wikitext: str) -> list[tuple[str, str]]:
    matches = list(_SECTION_RE.finditer(wikitext))
    result = []
    for i, match in enumerate(matches):
        heading = match.group(1).strip()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(wikitext)
        result.append((heading, wikitext[start:end]))
    return result


def _extract_existing_films(subpage_wikitext: str) -> list[str]:
    start = subpage_wikitext.find("==Existing==")
    if start == -1:
        return []
    end = subpage_wikitext.find("==Requested==", start)
    existing_wikitext = subpage_wikitext[
        start : end if end != -1 else len(subpage_wikitext)
    ]
    return [title.strip() for title in _FILM_LINK_RE.findall(existing_wikitext)]


def _dialogue_index(sections: list[tuple[str, str]]) -> int | None:
    for i, (heading, _) in enumerate(sections):
        if heading.strip().lower() == _DIALOGUE_HEADING:
            return i
    return None


def _extract_quote_candidates(film_wikitext: str) -> list[tuple[str, str]]:
    sections = _sections(film_wikitext)
    dialogue_index = _dialogue_index(sections)
    if dialogue_index is None:
        return []

    candidates: list[tuple[str, str]] = []
    for heading, body in sections[:dialogue_index]:
        if heading.strip().lower() in _EXCLUDED_HEADINGS:
            continue

        raw_bullets = _BULLET_RE.findall(body)
        if any(_parse_speaker_bullet(raw) is not None for raw in raw_bullets):
            # Section mixes multiple speakers inline (e.g. a catch-all "Others"
            # or "Quotes from <Source> Literature" section) rather than being a
            # single character's curated quotes — skip it entirely rather than
            # misattribute every line to the section heading.
            continue

        for raw in raw_bullets:
            line = _strip_emphasis(_strip_refs_and_links(raw))
            if not (1 <= _sentence_count(line) <= 2) or "http" in line:
                continue
            candidates.append((heading, line))
    return candidates


class WikiquoteMovieScraper(Scraper):

    async def _fetch_wikitext(
        self, client: httpx.AsyncClient, title: str
    ) -> str | None:
        response = await client.get(
            _API_URL,
            params={
                "action": "parse",
                "page": title,
                "prop": "wikitext",
                "format": "json",
                "formatversion": 2,
                "redirects": 1,
            },
        )
        response.raise_for_status()
        data = response.json()
        if "error" in data:
            logger.warning(
                "Wikiquote page %r missing or errored: %s", title, data["error"]
            )
            return None
        return data["parse"]["wikitext"]

    async def scrape(self) -> list[NewContent]:
        async with httpx.AsyncClient(
            timeout=30, headers={"User-Agent": _USER_AGENT}
        ) as client:
            main_wikitext = await self._fetch_wikitext(client, _MAIN_LIST_PAGE)
            if main_wikitext is None:
                return []

            subpage_titles = sorted(set(_SUBPAGE_TITLE_RE.findall(main_wikitext)))
            if not subpage_titles:
                logger.warning("No Wikiquote sub-page titles found on main list page")
                return []

            subpage_wikitext = await self._fetch_wikitext(
                client, random.choice(subpage_titles)
            )
            if subpage_wikitext is None:
                return []

            film_titles = _extract_existing_films(subpage_wikitext)
            if not film_titles:
                logger.warning("No existing films parsed from Wikiquote sub-page")
                return []

            film_title = random.choice(film_titles)
            film_wikitext = await self._fetch_wikitext(client, film_title)
            if film_wikitext is None:
                return []

            candidates = _extract_quote_candidates(film_wikitext)
            if not candidates:
                logger.warning("No usable quotes parsed for film %r", film_title)
                return []

            chosen = random.sample(
                candidates, min(len(candidates), _MAX_QUOTES_PER_FILM)
            )
            return [
                NewContent(
                    type=ContentType.LiteralQuote,
                    content=line,
                    author=author,
                    title=film_title,
                    literal_type=LiteralType.MOVIE,
                )
                for author, line in chosen
            ]


wikiquote_movie_scraper = WikiquoteMovieScraper()
