from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    SystemMessagePromptTemplate,
)
from langchain_openai import ChatOpenAI

from app.contents.enums import LanguageCode

_llm = ChatOpenAI(model="gpt-5.2", verbosity="medium", reasoning_effort="medium")

_system_prompt_template = SystemMessagePromptTemplate.from_template(
    """
You are a helpful assistant that translates quotes into the target language while preserving the original meaning and tone.
You should only translate the quote itself, without adding any extra explanations or comments.
"""
)

_user_prompt_template = HumanMessagePromptTemplate.from_template(
    """
# Target Language 
{target_language}

# Quote
{quote}
"""
)

_chat_prompt_template = ChatPromptTemplate.from_messages(
    [_system_prompt_template, _user_prompt_template]
)

_chain = _chat_prompt_template | _llm


async def translate(quote_text: str, target_language_code: LanguageCode) -> str:
    response = await _chain.ainvoke(
        {
            "quote": quote_text,
            "target_language": target_language_code.to_language_name(),
        }
    )
    return response.text
