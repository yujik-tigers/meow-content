import pytest

from app.analyzer.daily_quote_analyzer import daily_quote_analyzer
from app.analyzer.factory import AnalyzerFactory
from app.analyzer.literal_quote_analyzer import literal_quote_analyzer
from app.analyzer.meme_analyzer import reddit_meme_analyzer
from app.enums import ContentType


def test_get_analyzer_for_reddit_meme() -> None:
    """reddit_meme 타입 요청 시 reddit_meme_analyzer 싱글턴을 반환한다."""
    assert AnalyzerFactory.get_analyzer(ContentType.REDDIT_MEME) is reddit_meme_analyzer


def test_get_analyzer_for_quote() -> None:
    """quote 타입 요청 시 daily_quote_analyzer 싱글턴을 반환한다."""
    assert AnalyzerFactory.get_analyzer(ContentType.QUOTE) is daily_quote_analyzer


def test_get_analyzer_for_literal_quote() -> None:
    """literal_quote 타입 요청 시 literal_quote_analyzer 싱글턴을 반환한다."""
    assert (
        AnalyzerFactory.get_analyzer(ContentType.LiteralQuote) is literal_quote_analyzer
    )


def test_get_analyzer_raises_for_unsupported_content_type() -> None:
    """분석을 지원하지 않는 콘텐츠 타입이면 예외가 발생한다."""
    with pytest.raises(ValueError, match="Unsupported content type"):
        AnalyzerFactory.get_analyzer(ContentType.FACT)
