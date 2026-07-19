from dataclasses import replace
from typing import override

from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    SystemMessagePromptTemplate,
)
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from app.analyzer.base import ContentAnalyzer
from app.enums import ContentStatus
from app.schema.content import Content


class QuoteAnalyzeResult(BaseModel):
    quote_translation: str = Field(description="Korean translation of the full quote")
    expression: str = Field(
        description="A useful English word, phrase, idiom, or collocation extracted from the quote — something a Korean learner can actually use in real conversation"
    )
    expression_translation: str = Field(
        description="Korean translation of the extracted expression"
    )
    background: str = Field(
        description="Brief Korean explanation of the context behind this quote and what message it conveys"
    )


class DailyQuoteAnalyzer(ContentAnalyzer):

    def __init__(self) -> None:
        self._llm = ChatOpenAI(
            model="gpt-5.2", verbosity="medium", reasoning_effort="medium"
        )

    @override
    async def analyze_raw_content(self, content: Content) -> Content:
        system_prompt_template = SystemMessagePromptTemplate.from_template("""
        You are an English language education assistant that analyzes famous quotes for Korean learners.
        Your job is to surface one expression from the quote that is genuinely worth learning.

        Guidelines for choosing the expression:
        - Pick a word, phrase, idiom, or collocation that is genuinely useful — avoid overly basic words a beginner already knows (e.g. "good", "big", "go")
        - Prioritize expressions that native speakers use naturally in everyday conversation or writing
        - Good candidates: multi-word phrases ("fall into place"), idiomatic verb phrases ("give up on"), fixed collocations ("make a difference"), or notable grammatical patterns worth imitating

        Also:
        - Translate the full quote naturally into Korean
        - Provide accurate, natural-sounding Korean translations
        - For the background, briefly explain in Korean the context behind this quote and the core message it conveys — keep it concise
        """)
        human_prompt_template = HumanMessagePromptTemplate.from_template(
            'Quote: "{quote}"\nAuthor: {author}\n\nAnalyze this quote and extract one English expression for language learning.'
        )
        prompt = ChatPromptTemplate.from_messages(
            [
                system_prompt_template,
                human_prompt_template,
            ]
        )
        chain = prompt | self._llm.with_structured_output(QuoteAnalyzeResult)

        analysis_result = await chain.ainvoke(
            {"quote": content.content, "author": content.author}
        )
        if not isinstance(analysis_result, QuoteAnalyzeResult):
            raise ValueError("Unexpected analysis result type")

        return replace(
            content,
            content_translation=analysis_result.quote_translation,
            expression=analysis_result.expression,
            expression_translation=analysis_result.expression_translation,
            background=analysis_result.background,
            status=ContentStatus.ANALYZED,
        )

daily_quote_analyzer = DailyQuoteAnalyzer()
