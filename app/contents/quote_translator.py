from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    SystemMessagePromptTemplate,
)
from langchain_openai import ChatOpenAI

from app.contents.enums import LanguageCode


class QuoteTranslator:

    def __init__(self) -> None:
        llm = ChatOpenAI(model="gpt-5.2", verbosity="medium", reasoning_effort="medium")

        system_prompt_template = SystemMessagePromptTemplate.from_template(
            """
You are a helpful assistant that translates quotes into the target language while preserving the original meaning and tone.
You should only translate the quote itself, without adding any extra explanations or comments.
"""
        )

        user_prompt_template = HumanMessagePromptTemplate.from_template(
            """
# Target Language 
{target_language}

# Quote
{quote}
"""
        )

        chat_prompt_template = ChatPromptTemplate.from_messages(
            [system_prompt_template, user_prompt_template]
        )

        self._chain = chat_prompt_template | llm

    async def translate(self, quote: str, target_language_code: LanguageCode) -> str:
        response = await self._chain.ainvoke(
            {
                "quote": quote,
                "target_language": target_language_code.to_language_name(),
            }
        )
        return response.text


quote_translator = QuoteTranslator()
