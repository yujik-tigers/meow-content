from qdrant_client import AsyncQdrantClient
from qdrant_client.http.models import Distance, VectorParams

from app.settings import app_config

_CAT_FACT_VECTOR_SIZE = 1536

qdrant_client = AsyncQdrantClient(
    host=app_config.QDRANT_HOST, port=app_config.QDRANT_PORT
)


async def ensure_cat_fact_collection() -> None:
    exists = await qdrant_client.collection_exists(app_config.QDRANT_FACT_COLLECTION)
    if not exists:
        await qdrant_client.create_collection(
            collection_name=app_config.QDRANT_FACT_COLLECTION,
            vectors_config=VectorParams(
                size=_CAT_FACT_VECTOR_SIZE, distance=Distance.COSINE
            ),
        )
