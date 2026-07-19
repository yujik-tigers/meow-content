from dataclasses import replace
from typing import cast

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


class MemeAnalyzeResult(BaseModel):
    meme_text: str = Field(description="The exact text written on the meme image")
    meme_text_translation: str = Field(
        description="Korean translation of the text written on the meme image"
    )
    expressions: str = Field(
        description="A practical English expression (phrase, idiom, or colloquial usage) extracted from the meme — not a basic vocabulary word, but something intermediate-to-advanced learners can actually use in real conversation"
    )
    translation: str = Field(description="Korean translation of the expression")
    background: str = Field(
        description="Korean explanation of what this meme means",
    )


class RedditMemeAnalyzer(ContentAnalyzer):

    def __init__(self) -> None:
        self._llm = ChatOpenAI(
            model="gpt-5.2", verbosity="medium", reasoning_effort="medium"
        )

    async def analyze_raw_content(self, content: Content) -> Content:
        system_prompt_template = SystemMessagePromptTemplate.from_template("""
        You are an English language education assistant that analyzes meme images for Korean learners.
        Your job is to extract the meme text and surface one expression that is genuinely worth learning.

        Guidelines for choosing the expression:
        - Pick a phrase, idiom, slang term, or colloquial usage — NOT a standalone basic word (e.g. avoid "happy", "run", "big")
        - Prioritize expressions that native speakers actually say in everyday conversation or on social media
        - Prefer intermediate-to-advanced expressions: things a Korean learner probably hasn't studied in a textbook
        - Good candidates: multi-word phrases ("I can't even"), idioms ("throw under the bus"), sarcastic/ironic usages, internet slang with real-world applicability
        - If the meme text is very short or simple, extract the culturally meaningful usage pattern rather than just the words

        Also:
        - Extract the exact text shown on the meme
        - Provide accurate, natural-sounding Korean translations
        - Give a brief Korean explanation of what the meme means and when/how the expression is used
        """)
        human_prompt_template = HumanMessagePromptTemplate.from_template(
            [
                {"type": "image_url", "image_url": {"url": "{img_url}"}},
                {
                    "type": "text",
                    "text": "Analyze this meme and extract the English expression for language learning.",
                },
            ]
        )
        prompt = ChatPromptTemplate.from_messages(
            [
                system_prompt_template,
                human_prompt_template,
            ]
        )
        chain = prompt | self._llm.with_structured_output(MemeAnalyzeResult)

        analysis_result = await chain.ainvoke({"img_url": content.image_url})
        if not isinstance(analysis_result, MemeAnalyzeResult):
            raise ValueError("Unexpected analysis result type")
        analysis_result = cast(MemeAnalyzeResult, analysis_result)

        return replace(
            content,
            content=analysis_result.meme_text,
            content_translation=analysis_result.meme_text_translation,
            expression=analysis_result.expressions,
            expression_translation=analysis_result.translation,
            background=analysis_result.background,
            status=ContentStatus.PENDING,
        )

reddit_meme_analyzer = RedditMemeAnalyzer()
