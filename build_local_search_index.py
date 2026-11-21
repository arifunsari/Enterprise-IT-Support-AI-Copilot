"""Build the local FTS5 index from sample and locally uploaded documents."""

from pathlib import Path

from app.core.config import get_settings
from app.rag.retrieval import index_chunks, stable_chunk_id
from app.services.ingestion import SUPPORTED, chunk_documents, load_file


def main() -> None:
    settings = get_settings()
    roots = (Path(settings.sample_kb_dir), Path(settings.upload_dir))
    files = [
        path
        for root in roots
        if root.exists()
        for path in root.iterdir()
        if path.is_file() and path.suffix.lower() in SUPPORTED
    ]
    indexed_chunks = 0
    for path in files:
        chunks = chunk_documents(load_file(path))
        ids = [stable_chunk_id(chunk, index) for index, chunk in enumerate(chunks)]
        index_chunks(chunks, ids)
        indexed_chunks += len(chunks)
    print(f"Indexed {len(files)} local files -> {indexed_chunks} FTS5 chunks")


if __name__ == "__main__":
    main()
