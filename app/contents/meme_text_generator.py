import base64

from langchain_openai import ChatOpenAI

_llm = ChatOpenAI(model="gpt-5.2", verbosity="high", reasoning_effort="high")


def _bytes_to_base64(image_bytes: bytes) -> str:
    return base64.b64encode(image_bytes).decode()
