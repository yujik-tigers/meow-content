from app.analyzer.base import ContentAnalyzer
from app.analyzer.daily_quote_analyzer import daily_quote_analyzer
from app.analyzer.meme_analyzer import reddit_meme_analyzer
from app.enums import ContentType


class AnalyzerFactory:
    @staticmethod
    def get_analyzer(content_type: ContentType) -> ContentAnalyzer:
        if content_type == ContentType.REDDIT_MEME:
            return reddit_meme_analyzer
        if content_type == ContentType.QUOTE:
            return daily_quote_analyzer

        raise ValueError(f"Unsupported content type to analyze: {content_type}")
