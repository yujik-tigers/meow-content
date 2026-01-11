import base64

from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI


class ImageCreator:
    """A class to create images based on quotes using an LLM."""

    async def create_image(self, width: int, height: int, quote: str) -> bytes:
        """
        Create a simple PNG image with the given width, height, and quote text.
        """

        prompt_template = PromptTemplate.from_template(
            """
    Create a cat PNG image of size {width}x{height} that matches the given quote.
    Quote should be clearly visible on the image.
    Answer it BASE64 ENCODED PNG IMAGE DATA ONLY.

    # Quote "{quote}"
    """
        )

        llm = ChatOpenAI(model="gpt-5")

        chain = prompt_template | llm

        response = await chain.ainvoke(
            {"width": width, "height": height, "quote": quote}
        )
        return base64.b64decode(response.text)


image_creator = ImageCreator()
