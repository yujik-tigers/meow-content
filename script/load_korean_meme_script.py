"""
Load KREW/KoCulture-Descriptions dataset into Qdrant.

Run: python scripts/load_korean_meme_script.py
"""

from datetime import datetime

from datasets import load_dataset
from langchain_core.documents import Document

from app.vector.client import create_vector_store

_DATASET_NAME = "huggingface-KREW/KoCulture-Descriptions"


def _parse_date(date_str: str) -> int:
    if not date_str:
        return int(datetime(2000, 1, 1).timestamp())
    if len(date_str) == 4:
        return int(datetime(int(date_str), 1, 1).timestamp())
    return int(datetime.strptime(date_str, "%Y.%m.%d").timestamp())


def main() -> None:
    dataset = load_dataset(_DATASET_NAME, split="train")
    vector_store = create_vector_store()

    print("Columns:", dataset.column_names)
    print("Sample:", dataset[0])

    docs = [
        Document(
            page_content=row["content"],
            metadata={
                "id": row["title"],
                "date": _parse_date(row["date"]),
                "content": row["content"],
                "source": row["source"],
            },
        )
        for row in dataset.to_list()
    ]

    vector_store.add_documents(docs)
    print(f"Upserted {len(docs)} documents to Qdrant.")


if __name__ == "__main__":
    main()
