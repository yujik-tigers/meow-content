from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

from app.settings import app_config

from .embeddings import embeddings

_COLLECTION_NAME = "meme_keywords"
_VECTOR_SIZE = 1024  # gemini-embedding-001 with output_dimensionality=1024


def create_vector_store() -> QdrantVectorStore:
    client = QdrantClient(host=app_config.QDRANT_HOST, port=app_config.QDRANT_PORT)

    if not client.collection_exists(_COLLECTION_NAME):
        client.create_collection(
            collection_name=_COLLECTION_NAME,
            vectors_config=VectorParams(size=_VECTOR_SIZE, distance=Distance.COSINE),
        )

    return QdrantVectorStore(
        client=client,
        collection_name=_COLLECTION_NAME,
        embedding=embeddings,
    )
