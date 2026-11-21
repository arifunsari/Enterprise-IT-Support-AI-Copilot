import time
from pinecone import Pinecone , ServerlessSpec
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from app.core.config import get_settings
from app.rag.retrieval import index_chunks, stable_chunk_id

settings = get_settings()


_embeddings = None
_vectorstore = None


EMBEDDING_DIMENSIONS = {
    "text-embedding-3-small": 1536,
    "text-embedding-3-large": 3072,
    "text-embedding-ada-002": 1536,
    "all-minilm-l6-v2": 384,
}



def get_embedding_dimension(model_name: str | None = None) -> int:
    name = (model_name or settings.embedding_model or "").strip()
    if not name:
        raise RuntimeError("Embedding model is not configured")

    normalized = name.lower()
    if normalized in EMBEDDING_DIMENSIONS:
        return EMBEDDING_DIMENSIONS[normalized]
    if "text-embedding-3-small" in normalized:
        return 1536
    if "text-embedding-3-large" in normalized:
        return 3072
    if "text-embedding-ada-002" in normalized:
        return 1536
    if "all-minilm" in normalized:
        return 384

    raise ValueError(
        f"Unsupported embedding model '{model_name or settings.embedding_model}' for Pinecone. "
        "Add the matching dimension to EMBEDDING_DIMENSIONS."
    )



def get_embeddings():
    global _embeddings
    if _embeddings is None:
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is missing")
        _embeddings = OpenAIEmbeddings(
            model=settings.embedding_model,
            api_key=settings.openai_api_key,
        )
    return _embeddings




def ensure_index():
    if not settings.pinecone_api_key:
        raise RuntimeError("PINECONE_API_KEY is missing")

    desired_dimension = get_embedding_dimension()
    pc = Pinecone(api_key=settings.pinecone_api_key)
    names = [x["name"] for x in pc.list_indexes()]

    if settings.pinecone_index_name in names:
        index_info = pc.describe_index(settings.pinecone_index_name)
        current_dimension = getattr(index_info, "dimension", None)
        if current_dimension is None and isinstance(index_info, dict):
            current_dimension = index_info.get("dimension")

        if current_dimension is not None and current_dimension != desired_dimension:
            raise RuntimeError(
                f"Pinecone index '{settings.pinecone_index_name}' has dimension "
                f"{current_dimension}, but embedding model '{settings.embedding_model}' "
                f"requires {desired_dimension}. Set a compatible embedding model or "
                "configure a new Pinecone index; the existing index was not changed."
            )

    if settings.pinecone_index_name not in [x["name"] for x in pc.list_indexes()]:
        pc.create_index(
            name=settings.pinecone_index_name,
            dimension=desired_dimension,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1"),
        )
        while not pc.describe_index(settings.pinecone_index_name).status["ready"]:
            time.sleep(1)

    return pc.Index(settings.pinecone_index_name)





def get_vectorstore():
    global _vectorstore
    if _vectorstore is None:
        index = ensure_index()
        _vectorstore = PineconeVectorStore(
            index=index,
            embedding=get_embeddings(),
            namespace=settings.pinecone_namespace,
        )
    return _vectorstore



def get_retriever():
    candidate_k = settings.retrieval_candidate_k if settings.hybrid_retrieval_enabled else settings.top_k
    return get_vectorstore().as_retriever(search_kwargs={"k": candidate_k})



def add_documents(chunks, ids: list[str] | None = None):
    store = get_vectorstore()
    chunks = list(chunks)
    document_ids = ids or [stable_chunk_id(chunk, index) for index, chunk in enumerate(chunks)]
    if len(document_ids) != len(chunks):
        raise ValueError("Document IDs must match the number of chunks")
    for chunk_id, chunk in zip(document_ids, chunks, strict=True):
        chunk.metadata["_search_id"] = chunk_id
    stored_ids = store.add_documents(chunks, ids=document_ids)
    try:
        index_chunks(chunks, document_ids)
    except Exception:
        import logging
        logging.getLogger(__name__).exception("Local keyword index update failed")
    return stored_ids
