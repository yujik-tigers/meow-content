import base64
import logging
from datetime import date

from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import (
    CommaSeparatedListOutputParser,
    StrOutputParser,
)
from langchain_openai import ChatOpenAI
from langchain_qdrant import QdrantVectorStore

from app.client import cataas_client
from app.content import image_manager, image_text_renderer
from app.content.enums import ImageType

logger = logging.getLogger(__name__)


class MemeImageCreator:

    _FEW_SHOT_EXAMPLES = [
        "app/images/meme_example1.png",
        "app/images/meme_example2.png",
        "app/images/meme_example3.png",
        "app/images/meme_example4.png",
        "app/images/meme_example5.png",
        "app/images/meme_example6.png",
    ]

    def __init__(self, vector_store: QdrantVectorStore):
        self._llm = ChatOpenAI(
            model="gpt-5.2", verbosity="medium", reasoning_effort="medium"
        )
        self._vector_store = vector_store

    async def create(self, date: date) -> str:
        if image_manager.is_exist(
            date=date,
            image_type=ImageType.MEME,
        ):
            return image_manager.find_image_path_by(
                date=date,
                image_type=ImageType.MEME,
            )

        image = await cataas_client.get_daily_cat_image(date)

        keywords = await self._describe_image(image)
        memes = await self._search_meme_by_keywords(keywords, 0.8)
        meme_text = await self._generate_meme_text(image, memes)
        meme_image = image_text_renderer.add_meme(image, meme_text)
        meme_image_path = image_manager.save_image(
            image_bytes=meme_image,
            date=date,
            image_type=ImageType.MEME,
        )

        return meme_image_path

    def _load_examples(self) -> list[SystemMessage]:
        messages = []
        for idx, path in enumerate(self._FEW_SHOT_EXAMPLES, 1):
            with open(path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            messages.append(
                SystemMessage(
                    content=[
                        {
                            "type": "text",
                            "text": f"밈 예시{idx}\n\n",
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{b64}"},
                        },
                    ]
                )
            )
        return messages

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
                        "키워드는 한국어로, 쉼표로 구분해서 3개만 출력해. 설명이나 문장은 쓰지 마."
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

    async def _search_meme_by_keywords(
        self, keywords: list[str], threshold: float
    ) -> list[Document]:
        seen: dict[str, Document] = {}
        for doc, score in await self._vector_store.asimilarity_search_with_score(
            query=", ".join(keywords), k=3, score_threshold=threshold
        ):
            doc_id = doc.metadata["id"]
            if doc_id not in seen:
                seen[doc_id] = doc

            logger.info(
                "Keyword: %s, Meme: %s, Description: %s, Threshold: %f",
                ", ".join(keywords),
                doc.metadata["id"],
                doc.page_content,
                score,
            )
        return list(seen.values())

    async def _generate_meme_text(self, image: bytes, memes: list[Document]) -> str:
        b64 = base64.b64encode(image).decode()
        meme_references = "\n\n".join(
            f"{doc.metadata['id']}: {doc.page_content}" for doc in memes
        )
        return await (self._llm | StrOutputParser()).ainvoke(
            [
                SystemMessage(
                    content=(
                        "너는 고양이 이미지에 어울리는 재미있는 제목을 만드는 전문가야. "
                        "아래 예시들처럼 이미지의 상황과 고양이의 표정, 자세를 바탕으로 재밌는 텍스트를 만들어. "
                        "너무 길게 설명하지 말고, 최대한 간결하게 제목을 지어줘."
                        "부연 설명은 하지마.\n\n"
                    )
                ),
                *self._load_examples(),
                HumanMessage(
                    content=[
                        {
                            "type": "text",
                            "text": (
                                f"참고할 밈 표현:\n{meme_references}\n\n"
                                "이미지와 밈 표현을 참고해서 이 고양이 사진에 어울리는 밈 텍스트를 만들어줘.\n"
                                "반드시 모든 밈 표현을 사용할 필요는 없어. 가장 어울리는 표현을 참고해서 만들어줘."
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
