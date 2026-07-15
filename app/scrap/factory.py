from app.enums import ContentType
from app.scrap.base import Scraper
from app.scrap.daily_quote_scraper import daily_quote_scraper
from app.scrap.reddit_meme_scraper import reddit_meme_scraper


class ScraperFactory:
    @staticmethod
    def get_scraper(content_type: ContentType) -> Scraper:
        if content_type == ContentType.REDDIT_MEME:
            return reddit_meme_scraper
        if content_type == ContentType.QUOTE:
            return daily_quote_scraper

        raise ValueError(f"Unsupported content type to scrape: {content_type}")
