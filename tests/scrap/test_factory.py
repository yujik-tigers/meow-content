from typing import cast

import pytest

from app.enums import ContentType
from app.scrap.cat_fact_generator import cat_fact_generator
from app.scrap.daily_quote_scraper import daily_quote_scraper
from app.scrap.factory import ScraperFactory
from app.scrap.reddit_meme_scraper import reddit_meme_scraper
from app.scrap.wikiquote_movie_scraper import wikiquote_movie_scraper


def test_get_scraper_for_reddit_meme() -> None:
    """reddit_meme 타입 요청 시 RedditMemeScraper 싱글턴을 반환한다."""
    assert ScraperFactory.get_scraper(ContentType.REDDIT_MEME) is reddit_meme_scraper


def test_get_scraper_for_quote() -> None:
    """quote 타입 요청 시 DailyQuoteScraper 싱글턴을 반환한다."""
    assert ScraperFactory.get_scraper(ContentType.QUOTE) is daily_quote_scraper


def test_get_scraper_for_literal_quote() -> None:
    """literal_quote 타입 요청 시 WikiquoteMovieScraper 싱글턴을 반환한다."""
    assert (
        ScraperFactory.get_scraper(ContentType.LiteralQuote)
        is wikiquote_movie_scraper
    )


def test_get_scraper_for_fact() -> None:
    """fact 타입 요청 시 CatFactGenerator 싱글턴을 반환한다."""
    assert ScraperFactory.get_scraper(ContentType.FACT) is cat_fact_generator


def test_get_scraper_raises_for_unsupported_content_type() -> None:
    """스크래핑을 지원하지 않는 콘텐츠 타입이면 예외가 발생한다."""
    with pytest.raises(ValueError, match="Unsupported content type"):
        ScraperFactory.get_scraper(cast(ContentType, "unsupported"))
