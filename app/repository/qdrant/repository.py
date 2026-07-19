import logging
import uuid
from typing import Any, override

from langchain_core.callbacks.manager import (
    AsyncCallbackManagerForLLMRun,
    CallbackManagerForLLMRun,
)
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.messages.ai import UsageMetadata
from langchain_core.outputs import ChatGeneration, ChatResult
from openai import AsyncOpenAI
from openai.types import CreateEmbeddingResponse
from pydantic import Field, model_validator
from qdrant_client.http.models import PointStruct

from app.repository.qdrant.engine import qdrant_client
from app.settings import app_config

logger = logging.getLogger(__name__)


class _OpenAIEmbeddingChatModel(BaseChatModel):
    """Thin LangChain wrapper around the OpenAI Embeddings API so embedding
    calls flow through the same global token-usage tracking as chat calls
    (see app.usage.usage_tracking), mirroring
    app.image_generator.diffusion_model._GptImage2ChatModel."""

    model: str
    async_client: Any = Field(default=None, exclude=True)

    @model_validator(mode="after")
    def _init_client(self) -> "_OpenAIEmbeddingChatModel":
        self.async_client = AsyncOpenAI()
        return self

    @property
    @override
    def _llm_type(self) -> str:
        return "openai-embedding"

    @override
    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        raise NotImplementedError("_OpenAIEmbeddingChatModel only supports ainvoke")

    @override
    async def _agenerate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: AsyncCallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        text = messages[-1].content
        assert isinstance(text, str), "Embedding input must be plain text"

        response = await self.async_client.embeddings.create(
            model=self.model, input=text
        )

        return ChatResult(
            generations=[
                ChatGeneration(message=self._embedding_response_to_ai_message(response))
            ]
        )

    def _embedding_response_to_ai_message(
        self, response: CreateEmbeddingResponse
    ) -> AIMessage:
        usage_metadata = None
        if response.usage is not None:
            usage_metadata = UsageMetadata(
                input_tokens=response.usage.prompt_tokens,
                output_tokens=0,
                total_tokens=response.usage.total_tokens,
            )

        return AIMessage(
            content="",
            response_metadata={
                "model_name": self.model,
                "embedding": response.data[0].embedding,
            },
            usage_metadata=usage_metadata,
        )


class CatFactSimilarityRepository:
    def __init__(self) -> None:
        self._embedder = _OpenAIEmbeddingChatModel(model=app_config.OPENAI_EMBEDDING_MODEL)

    async def is_duplicate(self, text: str) -> bool:
        """Returns True if `text` is a near-duplicate of already-inserted content."""
        vector = await self._embed(text)

        result = await qdrant_client.query_points(
            collection_name=app_config.QDRANT_FACT_COLLECTION,
            query=vector,
            limit=1,
        )
        if not result.points:
            return False

        matched = result.points[0]
        if matched.score < app_config.FACT_SIMILARITY_THRESHOLD:
            return False

        logger.info(
            "Found duplicate fact (score=%.4f)\n  new: %r\n  existing: %r",
            matched.score,
            text,
            matched.payload.get("content") if matched.payload else None,
        )
        return True

    async def insert(self, text: str) -> None:
        vector = await self._embed(text)
        await qdrant_client.upsert(
            collection_name=app_config.QDRANT_FACT_COLLECTION,
            points=[
                PointStruct(id=str(uuid.uuid4()), vector=vector, payload={"content": text})
            ],
        )

    async def _embed(self, text: str) -> list[float]:
        result = await self._embedder.ainvoke(text)
        return result.response_metadata["embedding"]


cat_fact_similarity_repository = CatFactSimilarityRepository()
