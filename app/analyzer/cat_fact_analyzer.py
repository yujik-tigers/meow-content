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


class CatFactAnalyzeResult(BaseModel):
    fact_translation: str = Field(description="Korean translation of the full fact")
    background: str = Field(
        description="Brief Korean explanation adding context or color to the fact — why it's true, or what makes it interesting"
    )


class CatFactAnalyzer(ContentAnalyzer):

    def __init__(self) -> None:
        self._llm = ChatOpenAI(
            model="gpt-5.2", verbosity="medium", reasoning_effort="medium"
        )

    @override
    async def analyze_raw_content(self, content: Content) -> Content:
        system_prompt_template = SystemMessagePromptTemplate.from_template("""
        You are a Korean-language assistant that prepares fun cat facts for a daily cat-content mailing list.

        Your job is to:
        - Translate the fact naturally and accurately into Korean
        - Provide a brief Korean explanation of the context behind the fact — why it's true or what makes it interesting — keep it concise
        """)
        human_prompt_template = HumanMessagePromptTemplate.from_template(
            'Fact: "{fact}"\n\nTranslate this fact and provide brief background context.'
        )
        prompt = ChatPromptTemplate.from_messages(
            [
                system_prompt_template,
                human_prompt_template,
            ]
        )
        chain = prompt | self._llm.with_structured_output(CatFactAnalyzeResult)

        analysis_result = await chain.ainvoke({"fact": content.content})
        if not isinstance(analysis_result, CatFactAnalyzeResult):
            raise ValueError("Unexpected analysis result type")

        return replace(
            content,
            content_translation=analysis_result.fact_translation,
            background=analysis_result.background,
            status=ContentStatus.ANALYZED,
        )

cat_fact_analyzer = CatFactAnalyzer()
