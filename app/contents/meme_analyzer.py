from typing import cast

from langchain.messages import HumanMessage
from langchain_core.prompts import SystemMessagePromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field


class MemeAnalyzeResult(BaseModel):
    meme_text: str = Field(description="The exact text written on the meme image")
    expressions: str = Field(
        description="The most useful English word or idiom for language learning extracted from the meme text"
    )
    translation: str = Field(description="Korean translation of the expression")
    background: str | None = Field(
        default=None,
        description="Korean explanation of the cultural background, origin, or usage context — only when the expression is slang, internet slang, abbreviation, or culturally specific term that requires extra context to understand",
    )


_llm = ChatOpenAI(model="gpt-5.2", verbosity="medium", reasoning_effort="medium")

_system_prompt_template = SystemMessagePromptTemplate.from_template("""
You are an English language education assistant that analyzes meme images.
Your job is to extract the meme text and identify the single most valuable English expression for Korean learners.

Guidelines:
- Extract the exact text displayed on the meme image
- Choose one expression (word, phrase, or idiom) that is most useful for English learning
- Prefer idiomatic expressions, slang, or culturally significant phrases over common words
- Provide an accurate and natural Korean translation
- If the expression is slang, internet slang, abbreviation, or a culturally specific term, add a Korean background explanation covering its origin, how it's used, or why it has that meaning. Otherwise leave it null.
""")

_chain = _llm.with_structured_output(MemeAnalyzeResult)


async def analyze_meme(img_url: str) -> MemeAnalyzeResult:
    messages = [
        _system_prompt_template.format_messages()[0],
        HumanMessage(
            content=[
                {"type": "image_url", "image_url": {"url": img_url}},
                {
                    "type": "text",
                    "text": "Analyze this meme and extract the English expression for language learning.",
                },
            ]
        ),
    ]

    return cast(MemeAnalyzeResult, await _chain.ainvoke(messages))
