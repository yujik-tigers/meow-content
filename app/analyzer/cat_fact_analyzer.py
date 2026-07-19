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

    @override
    async def reanalyze_content_field(
        self,
        current_content: Content,
        fields: list[ReanalyzeContentField],
    ) -> Content:
        field_defs: dict[str, Any] = {
            (
                "fact_translation"
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
                f"- fact: {current_content.content}",
                f"- fact_translation: {current_content.content_translation}",
                f"- background: {current_content.background}",
            ]
        )
        fields_instruction = "\n".join(
            f"- {f.field_name}: {f.prompt_guide}" for f in fields
        )

        system = SystemMessagePromptTemplate.from_template(
            "You are re-evaluating specific fields of an already-analyzed cat fact for a Korean audience. "
            "Use the fact and current field values as context. "
            "Follow each field's prompt guide strictly. Only output the requested fields."
        )
        human = HumanMessagePromptTemplate.from_template(
            'Fact: "{fact}"\n\nCurrent field values:\n{current_values}\n\nFields to re-generate:\n{fields_instruction}'
        )
        prompt = ChatPromptTemplate.from_messages([system, human])
        chain = prompt | self._llm.with_structured_output(dynamic_model)

        result = await chain.ainvoke(
            {
                "fact": current_content.content,
                "current_values": current_values,
                "fields_instruction": fields_instruction,
            }
        )

        updates: dict[str, Any] = {
            ("content_translation" if k == "fact_translation" else k): v
            for k, v in cast(BaseModel, result).model_dump().items()
        }
        return replace(current_content, **updates, status=ContentStatus.ANALYZED)


cat_fact_analyzer = CatFactAnalyzer()
