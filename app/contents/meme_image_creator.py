import base64
from datetime import date

from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import (
    CommaSeparatedListOutputParser,
    StrOutputParser,
)
from langchain_openai import ChatOpenAI

from app.clients import cataas_client
from app.contents import image_manager, image_text_renderer
from app.contents.enums import ImageType, LanguageCode
from app.vector.client import vector_store


class MemeImageCreator:
    def __init__(self):
        self._llm = ChatOpenAI(
            model="gpt-5.2", verbosity="medium", reasoning_effort="medium"
        )

    async def create(self, date: date) -> str:
        if image_manager.is_exist(
            language_code=LanguageCode.KOREAN,
            date=date,
            image_type=ImageType.MEME,
        ):
            return image_manager.find_image_path_by(
                language_code=LanguageCode.KOREAN,
                date=date,
                image_type=ImageType.MEME,
            )

        image = await cataas_client.get_daily_cat_image(date)

        keywords = await self._describe_image(image)
        memes = await self._search_meme_by_keywords(keywords)
        meme_text = await self._generate_meme_text(image, keywords, memes)
        meme_image = image_text_renderer.add_meme(image, meme_text)
        meme_image_path = image_manager.save_image(
            image_bytes=meme_image,
            language_code=LanguageCode.KOREAN,
            date=date,
            image_type=ImageType.MEME,
        )

        return meme_image_path

    async def _describe_image(self, image: bytes) -> list[str]:
        b64 = base64.b64encode(image).decode()
        self._describe_chain = self._llm | CommaSeparatedListOutputParser()

        return await self._describe_chain.ainvoke(
            [
                SystemMessage(
                    content=(
                        "너는 이미지를 분석해서 인터넷 밈 검색에 적합한 키워드를 추출하는 전문가야. "
                        "주어진 이미지의 분위기, 감정, 상황을 파악하고, "
                        "벡터 DB에서 어울리는 밈을 찾기 위한 핵심 키워드만 추출해. "
                        "키워드는 한국어로, 쉼표로 구분해서 3~5개만 출력해. 설명이나 문장은 쓰지 마."
                    )
                ),
                HumanMessage(
                    content=[
                        {
                            "type": "text",
                            "text": "이 이미지에 어울리는 밈 키워드를 추출해줘.",
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
                        },
                    ]
                ),
            ]
        )

    async def _search_meme_by_keywords(self, keywords: list[str]) -> list[Document]:
        seen: dict[str, Document] = {}
        for keyword in keywords:
            for doc in await vector_store.asimilarity_search(query=keyword, k=1):
                doc_id = doc.metadata["id"]
                if doc_id not in seen:
                    seen[doc_id] = doc
        return list(seen.values())

    async def _generate_meme_text(
        self, image: bytes, description: list[str], memes: list[Document]
    ) -> str:
        b64 = base64.b64encode(image).decode()
        meme_references = "\n".join(f"- {doc.page_content}" for doc in memes)
        return await (self._llm | StrOutputParser()).ainvoke(
            [
                SystemMessage(
                    content=(
                        "너는 고양이 이미지에 어울리는 재미있는 이미지 제목을 만드는 전문가야. "
                        "이미지 제목만 출력해. 부연 설명은 하지마."
                    )
                ),
                HumanMessage(
                    content=[
                        {
                            "type": "text",
                            "text": (
                                f"이미지를 표현하는 키워드: {', '.join(description)}\n\n"
                                f"참고할 밈 표현:\n{meme_references}\n\n"
                                "이미지와 키워드, 밈 표현을 참고해서 이 고양이 사진에 어울리는 이미지 제목을 만들어줘."
                            ),
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
                        },
                    ]
                ),
            ]
        )


meme_image_creator = MemeImageCreator()
