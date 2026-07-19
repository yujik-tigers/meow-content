from app.enums import ContentType
from app.scrap.base import Scraper
from app.scrap.cat_fact_generator import cat_fact_generator
from app.scrap.daily_quote_scraper import daily_quote_scraper
from app.scrap.reddit_meme_scraper import reddit_meme_scraper
from app.scrap.wikiquote_movie_scraper import wikiquote_movie_scraper


class ScraperFactory:
    @staticmethod
    def get_scraper(content_type: ContentType) -> Scraper:
        if content_type == ContentType.REDDIT_MEME:
            return reddit_meme_scraper
        if content_type == ContentType.QUOTE:
            return daily_quote_scraper
        if content_type == ContentType.LiteralQuote:
            return wikiquote_movie_scraper
        if content_type == ContentType.FACT:
            return cat_fact_generator

        raise ValueError(f"Unsupported content type to scrape: {content_type}")
