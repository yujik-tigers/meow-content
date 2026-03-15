import base64

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

from app.contents import image_retriever
from app.contents.enums import LanguageCode

_llm = ChatOpenAI(model="gpt-5.2", verbosity="high", reasoning_effort="high")


def _bytes_to_base64(image_bytes: bytes) -> str:
    return base64.b64encode(image_bytes).decode()


async def generate_speech_bubble_text(
    image_bytes: bytes, language_code: LanguageCode
) -> str:
    """Use GPT vision with few-shot meme examples to generate funny speech bubble text."""

    examples = [
        image_retriever.retrieve_meme_sample(),
        image_retriever.retrieve_meme_sample(number=2),
        image_retriever.retrieve_meme_sample(number=3),
    ]
    language_name = language_code.to_language_name()

    content: list = [
        {
            "type": "text",
            "text": (
                f"You are a meme text generator. "
                f"Below are {len(examples)} example cat memes that already have funny speech bubble text on them. "
                "Study their humor style: gen-Z internet humor, relatable, slightly absurd, casual tone, "
                "typos and informal language are fine. "
                f"Then generate speech bubble text in {language_name} for the new cat image. "
                "Output ONLY the speech bubble text (1–2 short lines), nothing else."
            ),
        },
    ]

    for idx, img in enumerate(examples, 1):
        content.append({"type": "text", "text": f"Example {idx}:"})
        content.append(
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{_bytes_to_base64(img)}",
                },
            }
        )

    content.append(
        {"type": "text", "text": "Now generate funny speech bubble text for this cat:"}
    )
    content.append(
        {
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{_bytes_to_base64(image_bytes)}",
            },
        }
    )

    response = await _llm.ainvoke([HumanMessage(content=content)])
    print("Generated meme text:", response.text)
    return response.text.strip()
