"""Local lexical indexing and hybrid dense/keyword result fusion."""

import hashlib
import json
import logging
import re
import sqlite3
from pathlib import Path
from typing import Iterable

from langchain_core.documents import Document

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "can", "do", "for",
    "from", "how", "i", "in", "is", "it", "me", "my", "of", "on", "or",
    "our", "the", "to", "what", "when", "where", "which", "with", "you",
}


def _connect() -> sqlite3.Connection:
    Path(settings.audit_db_path).parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(settings.audit_db_path, timeout=10)
    connection.execute(
        "CREATE VIRTUAL TABLE IF NOT EXISTS chunk_fts USING fts5(chunk_id UNINDEXED, content, metadata UNINDEXED)"
    )
    return connection


def stable_chunk_id(document: Document, index: int) -> str:
    source = str(document.metadata.get("source", ""))
    page = document.metadata.get("page", document.metadata.get("page_label", ""))
    position = document.metadata.get("start_index", index)
    value = f"{source}\0{page}\0{position}\0{document.page_content}"
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def index_chunks(chunks: Iterable[Document], ids: list[str]) -> None:
    """Upsert chunk text into the local FTS index after Pinecone insertion."""
    rows = []
    for chunk_id, chunk in zip(ids, chunks, strict=True):
        chunk.metadata["_search_id"] = chunk_id
        metadata = {key: value for key, value in chunk.metadata.items() if key != "_rrf_score"}
        rows.append((chunk_id, chunk.page_content, json.dumps(metadata, default=str)))
    if not rows:
        return
    connection = _connect()
    try:
        with connection:
            connection.executemany("DELETE FROM chunk_fts WHERE chunk_id = ?", [(row[0],) for row in rows])
            connection.executemany(
                "INSERT INTO chunk_fts(chunk_id, content, metadata) VALUES (?, ?, ?)", rows
            )
    finally:
        connection.close()


def search_lexical(query: str, limit: int) -> list[Document]:
    terms = [term for term in re.findall(r"[\w]+", query.casefold()) if term not in _STOP_WORDS]
    if not terms:
        return []
    match_query = " OR ".join('"' + term + '"' for term in terms)
    try:
        connection = _connect()
    except sqlite3.OperationalError:
        logger.exception("SQLite FTS5 is unavailable; keyword retrieval is disabled")
        return []
    try:
        rows = connection.execute(
            "SELECT chunk_id, content, metadata FROM chunk_fts WHERE chunk_fts MATCH ? ORDER BY rank LIMIT ?",
            (match_query, limit),
        ).fetchall()
    finally:
        connection.close()
    documents = []
    for chunk_id, content, metadata_json in rows:
        metadata = json.loads(metadata_json)
        metadata["_search_id"] = chunk_id
        documents.append(Document(page_content=content, metadata=metadata))
    return documents


def _identity(document: Document) -> str:
    return hashlib.sha256(document.page_content.encode("utf-8")).hexdigest()


def fuse_and_rerank(query: str, dense_docs: list[Document], keyword_docs: list[Document], limit: int) -> list[Document]:
    """Fuse ranked lists with reciprocal rank fusion, then apply a lexical relevance pass."""
    scores: dict[str, float] = {}
    candidates: dict[str, Document] = {}
    for results in (dense_docs, keyword_docs):
        for rank, document in enumerate(results, start=1):
            key = _identity(document)
            candidates.setdefault(key, document)
            scores[key] = scores.get(key, 0.0) + 1.0 / (60 + rank)

    query_terms = {term for term in re.findall(r"[\w]+", query.casefold()) if term not in _STOP_WORDS}
    if not candidates:
        return []
    max_fusion = max(scores.values()) or 1.0

    def score(item: tuple[str, Document]) -> float:
        key, document = item
        content = document.page_content.casefold()
        doc_terms = set(re.findall(r"[\w]+", content))
        coverage = len(query_terms & doc_terms) / max(1, len(query_terms))
        phrase = 0.1 if query.strip().casefold() in content else 0.0
        return 0.5 * (scores[key] / max_fusion) + 0.4 * coverage + phrase

    ranked = sorted(candidates.items(), key=score, reverse=True)
    return [document for _, document in ranked[:limit]]


def retrieve_hybrid(query: str, dense_docs: list[Document], candidate_limit: int, result_limit: int) -> list[Document]:
    keyword_docs = search_lexical(query, candidate_limit)
    return fuse_and_rerank(query, dense_docs, keyword_docs, result_limit)
