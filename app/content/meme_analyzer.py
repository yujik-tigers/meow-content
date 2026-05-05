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
    background: str = Field(
        description="Korean explanation of what this meme means and why it's funny",
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
- Always provide a brief Korean background explanation describing what the meme means and why it's funny
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
