from dataclasses import replace
from typing import Any, cast, override

from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    SystemMessagePromptTemplate,
)
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field, create_model

from app.analyzer.base import ContentAnalyzer
from app.enums import ContentStatus
from app.schema.content import Content, ReanalyzeContentField


class LiteralQuoteAnalyzeResult(BaseModel):
    quote_translation: str = Field(description="Korean translation of the full quote")
    expression: str = Field(
        description="A useful English word, phrase, idiom, or collocation extracted from the quote — something a Korean learner can actually use in real conversation"
    )
    expression_translation: str = Field(
        description="Korean translation of the extracted expression"
    )
    background: str = Field(
        description="Brief Korean explanation of who says this line in the movie, in what scene or situation, and what it conveys"
    )


class LiteralQuoteAnalyzer(ContentAnalyzer):

    def __init__(self) -> None:
        self._llm = ChatOpenAI(
            model="gpt-5.2", verbosity="medium", reasoning_effort="medium"
        )

    @override
    async def analyze_raw_content(self, content: Content) -> Content:
        system_prompt_template = SystemMessagePromptTemplate.from_template("""
        You are an English language education assistant that analyzes memorable movie quotes for Korean learners.
        Your job is to surface one expression from the quote that is genuinely worth learning.

        Guidelines for choosing the expression:
        - Pick a word, phrase, idiom, or collocation that is genuinely useful — avoid overly basic words a beginner already knows (e.g. "good", "big", "go")
        - Prioritize expressions that native speakers use naturally in everyday conversation or writing
        - Good candidates: multi-word phrases ("fall into place"), idiomatic verb phrases ("give up on"), fixed collocations ("make a difference"), or notable grammatical patterns worth imitating

        Also:
        - Translate the full quote naturally into Korean, preserving the character's tone and voice
        - Provide accurate, natural-sounding Korean translations
        - For the background, briefly explain in Korean who says this line, in what scene or situation, and what it conveys — keep it concise
        """)
        human_prompt_template = HumanMessagePromptTemplate.from_template(
            'Movie: "{title}"\nQuote: "{quote}"\nSpeaker: {author}\n\nAnalyze this movie quote and extract one English expression for language learning.'
        )
        prompt = ChatPromptTemplate.from_messages(
            [
                system_prompt_template,
                human_prompt_template,
            ]
        )
        chain = prompt | self._llm.with_structured_output(LiteralQuoteAnalyzeResult)

        analysis_result = await chain.ainvoke(
            {
                "title": content.title,
                "quote": content.content,
                "author": content.author,
            }
        )
        if not isinstance(analysis_result, LiteralQuoteAnalyzeResult):
            raise ValueError("Unexpected analysis result type")

        return replace(
            content,
            content_translation=analysis_result.quote_translation,
            expression=analysis_result.expression,
            expression_translation=analysis_result.expression_translation,
            background=analysis_result.background,
            status=ContentStatus.ANALYZED,
        )

    @override
    async def reanalyze_content_field(
        self,
        current_content: Content,
        fields: list[ReanalyzeContentField],
    ) -> Content:
        field_defs: dict[str, Any] = {
            (
                "quote_translation"
                if f.field_name == "content_translation"
                else f.field_name
            ): (
                str,
                Field(description=f.prompt_guide),
            )
            for f in fields
        }
        dynamic_model = create_model("ReanalyzeResult", **field_defs)

        current_values = "\n".join(
            [
                f"- movie: {current_content.title}",
                f"- quote: {current_content.content}",
                f"- speaker: {current_content.author}",
                f"- quote_translation: {current_content.content_translation}",
                f"- expression: {current_content.expression}",
                f"- expression_translation: {current_content.expression_translation}",
                f"- background: {current_content.background}",
            ]
        )
        fields_instruction = "\n".join(
            f"- {f.field_name}: {f.prompt_guide}" for f in fields
        )

        system = SystemMessagePromptTemplate.from_template(
            "You are re-evaluating specific fields of an already-analyzed movie quote for Korean English learners. "
            "Use the movie title, quote, speaker, and current field values as context. "
            "Follow each field's prompt guide strictly. Only output the requested fields."
        )
        human = HumanMessagePromptTemplate.from_template(
            'Movie: "{title}"\nQuote: "{quote}"\nSpeaker: {author}\n\nCurrent field values:\n{current_values}\n\nFields to re-generate:\n{fields_instruction}'
        )
        prompt = ChatPromptTemplate.from_messages([system, human])
        chain = prompt | self._llm.with_structured_output(dynamic_model)

        result = await chain.ainvoke(
            {
                "title": current_content.title,
                "quote": current_content.content,
                "author": current_content.author,
                "current_values": current_values,
                "fields_instruction": fields_instruction,
            }
        )

        updates: dict[str, Any] = {
            ("content_translation" if k == "quote_translation" else k): v
            for k, v in cast(BaseModel, result).model_dump().items()
        }
        return replace(current_content, **updates, status=ContentStatus.ANALYZED)


literal_quote_analyzer = LiteralQuoteAnalyzer()
