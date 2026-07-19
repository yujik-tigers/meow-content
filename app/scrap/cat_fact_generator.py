from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    SystemMessagePromptTemplate,
)
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from app.enums import ContentType
from app.repository.qdrant.repository import cat_fact_similarity_repository
from app.schema.content import NewContent
from app.scrap.base import Scraper

_FACTS_PER_BATCH = 10


class CatFactBatch(BaseModel):
    facts: list[str] = Field(
        description="A list of distinct, verifiable, interesting facts about cats, "
        "each 1-2 sentences long"
    )


class CatFactGenerator(Scraper):

    def __init__(self) -> None:
        self._llm = ChatOpenAI(
            model="gpt-5.2", verbosity="medium", reasoning_effort="medium"
        )

    async def scrape(self) -> list[NewContent]:
        system_prompt_template = SystemMessagePromptTemplate.from_template("""
        You generate fun, surprising, and verifiably true facts about cats for a
        daily cat-content mailing list.

        Guidelines:
        - Each fact must be true and checkable, not folklore or urban legend
        - Prefer surprising or delightful facts over commonly-known ones (e.g. avoid "cats sleep a lot")
        - Keep each fact to 1-2 sentences
        - Make each fact in the batch distinct from the others — no rephrasing of the same fact
        """)
        human_prompt_template = HumanMessagePromptTemplate.from_template(
            f"Generate {_FACTS_PER_BATCH} distinct facts about cats."
        )
        prompt = ChatPromptTemplate.from_messages(
            [
                system_prompt_template,
                human_prompt_template,
            ]
        )
        chain = prompt | self._llm.with_structured_output(CatFactBatch)

        result = await chain.ainvoke({})
        if not isinstance(result, CatFactBatch):
            raise ValueError("Unexpected generation result type")

        new_contents: list[NewContent] = []
        for text in result.facts:
            if await cat_fact_similarity_repository.is_duplicate(text):
                continue
            await cat_fact_similarity_repository.insert(text)
            new_contents.append(NewContent(type=ContentType.FACT, content=text))

        return new_contents


cat_fact_generator = CatFactGenerator()
