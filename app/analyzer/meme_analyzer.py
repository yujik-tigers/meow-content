from dataclasses import replace
from typing import Any, NamedTuple, cast

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

    async def reanalyze_content_field(
        self,
        current_content: Content,
        fields: list[ReanalyzeContentField],
    ) -> Content:
        field_defs: dict[str, Any] = {
            _ADMIN_CONTENT_TO_LLM_SCHEMA[f.field_name].llm_field: (
                str,
                Field(
                    description=f"{_ADMIN_CONTENT_TO_LLM_SCHEMA[f.field_name].description}. \nPrompt guide: {f.prompt_guide}"
                ),
            )
            for f in fields
        }
        dynamic_model = create_model("ReanalyzeResult", **field_defs)

        current_values = "\n".join(
            [
                f"- meme_text: {current_content.content}",
                f"- meme_text_translation: {current_content.content_translation}",
                f"- expressions: {current_content.expression}",
                f"- translation: {current_content.expression_translation}",
                f"- background: {current_content.background}",
            ]
        )
        fields_instruction = "\n".join(
            f"- {f.field_name}: {f.prompt_guide}" for f in fields
        )

        system = SystemMessagePromptTemplate.from_template(
            "You are re-evaluating specific fields of an already-analyzed meme for Korean English learners. "
            "Use the meme image and current field values as context. "
            "Follow each field's prompt guide strictly. Only output the requested fields."
        )
        human = HumanMessagePromptTemplate.from_template(
            [
                {"type": "image_url", "image_url": {"url": "{img_url}"}},
                {
                    "type": "text",
                    "text": "Current field values:\n{current_values}\n\nFields to re-generate:\n{fields_instruction}",
                },
            ]
        )
        prompt = ChatPromptTemplate.from_messages([system, human])
        chain = prompt | self._llm.with_structured_output(dynamic_model)

        result = await chain.ainvoke(
            {
                "img_url": current_content.image_url,
                "current_values": current_values,
                "fields_instruction": fields_instruction,
            }
        )

        updates: dict[str, Any] = {
            _LLM_SCHEMA_TO_ADMIN_CONTENT[k]: v
            for k, v in cast(BaseModel, result).model_dump().items()
        }
        return replace(current_content, **updates, status=ContentStatus.PENDING)


class _LLMFieldSchema(NamedTuple):
    llm_field: str
    description: str


_ADMIN_CONTENT_TO_LLM_SCHEMA: dict[str, _LLMFieldSchema] = {
    "content": _LLMFieldSchema("meme_text", "The exact text on the meme"),
    "content_translation": _LLMFieldSchema(
        "meme_text_translation", "Korean translation of the meme text"
    ),
    "expression": _LLMFieldSchema(
        "expressions", "Practical English expression extracted from the meme"
    ),
    "expression_translation": _LLMFieldSchema(
        "translation", "Korean translation of the expression"
    ),
    "background": _LLMFieldSchema(
        "background",
        "Korean explanation of what the meme means and how the expression is used",
    ),
}

_LLM_SCHEMA_TO_ADMIN_CONTENT: dict[str, str] = {
    v[0]: k for k, v in _ADMIN_CONTENT_TO_LLM_SCHEMA.items()
}

reddit_meme_analyzer = RedditMemeAnalyzer()
