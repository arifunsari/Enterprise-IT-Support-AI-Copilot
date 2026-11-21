import hashlib
import json
import logging
import secrets
from pathlib import Path
from uuid import uuid4
from fastapi import APIRouter, UploadFile, File, HTTPException, Header
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from app.core.config import get_settings
from app.rag.workflow import ask, ask_stream
from app.rag.vectorstore import add_documents
from app.rag.retrieval import index_chunks
from app.services.ingestion import load_file, chunk_documents, SUPPORTED
from app.services.audit import write_audit, reserve_document, set_document_status

router = APIRouter(prefix="/api")
settings = get_settings()
logger = logging.getLogger(__name__)

#out user should be able to ask a question and get an answer from the knowledge base
class ChatRequest(BaseModel):
    question: str = Field(min_length=2, max_length=3000)


@router.get("/health")
def health():
    return {"status": "ok", "service": settings.app_name}


@router.post("/chat")
def chat(payload: ChatRequest):
    try:
        result = ask(payload.question)
        write_audit(payload.question, result["source_used"], result.get("trace", []))

        return {
            "answer": result["answer"],
            "source_used": result["source_used"],
            "trace": result.get("trace", []),
            "citations": result.get("citations", []),
            "rewritten_query": result.get("current_query", payload.question),
        }

    except Exception:
        logger.exception("Chat request failed")
        raise HTTPException(status_code=500, detail="The request could not be completed") from None


@router.post("/chat/stream")
def chat_stream(payload: ChatRequest):
    def events():
        try:
            for event in ask_stream(payload.question):
                if event.get("type") == "complete":
                    write_audit(payload.question, event["source_used"], event.get("trace", []))
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except Exception:
            logger.exception("Streaming chat request failed")
            yield f"data: {json.dumps({'type': 'error', 'detail': 'The request could not be completed'})}\n\n"

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/ingest")
async def ingest(file: UploadFile = File(...), x_admin_key: str = Header(default="")):
    if not settings.admin_api_key:
        raise HTTPException(status_code=503, detail="Document ingestion is not configured")
    if not secrets.compare_digest(x_admin_key, settings.admin_api_key):
        raise HTTPException(status_code=401, detail="Invalid admin key")
    suffix = Path(file.filename or "").suffix.lower()
    display_name = Path((file.filename or "document").replace("\\", "/")).name
    if suffix not in SUPPORTED:
        raise HTTPException(status_code=415, detail=f"Supported file types: {', '.join(sorted(SUPPORTED))}")
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    dest = upload_dir / f"{uuid4().hex}{suffix}"
    digest = hashlib.sha256()
    total = 0
    try:
        with dest.open("xb") as output:
            while True:
                block = await file.read(64 * 1024)
                if not block:
                    break
                total += len(block)
                if total > settings.max_upload_size_bytes:
                    raise HTTPException(status_code=413, detail="Uploaded file exceeds the size limit")
                digest.update(block)
                output.write(block)
        if total == 0:
            raise HTTPException(status_code=400, detail="Uploaded file is empty")
        sha256 = digest.hexdigest()
        document_id, prior_status = reserve_document(sha256)
        if prior_status == "completed":
            # Backfill the local FTS index for documents uploaded before hybrid search.
            try:
                duplicate_docs = chunk_documents(load_file(dest))
                for index, chunk in enumerate(duplicate_docs):
                    chunk.metadata.update({"document_id": document_id, "sha256": sha256})
                index_chunks(duplicate_docs, [f"{document_id}:{index}" for index in range(len(duplicate_docs))])
            except Exception:
                logger.exception("Keyword index backfill failed for duplicate document_id=%s", document_id)
            dest.unlink(missing_ok=True)
            return {"message": "Document already indexed", "file": display_name, "document_id": document_id, "status": "completed", "duplicate": True, "chunks": 0, "ids_created": 0}
        if prior_status in {"pending", "processing"}:
            dest.unlink(missing_ok=True)
            raise HTTPException(status_code=409, detail="This document is already being ingested")
        set_document_status(sha256, "processing")
        try:
            docs = load_file(dest)
        except Exception:
            # Loader exceptions vary by file format; details stay in server logs.
            set_document_status(sha256, "failed")
            logger.exception("Uploaded document parsing failed for format=%s", suffix)
            raise HTTPException(status_code=422, detail="Uploaded file content is invalid") from None
        try:
            chunks = chunk_documents(docs)
        except Exception:
            set_document_status(sha256, "failed")
            logger.exception("Document chunking failed for document_id=%s", document_id)
            raise HTTPException(status_code=422, detail="Uploaded document could not be prepared") from None
        if not chunks:
            set_document_status(sha256, "failed")
            raise HTTPException(status_code=422, detail="Uploaded document contains no readable text")
        for index, chunk in enumerate(chunks):
            chunk.metadata.update({"document_id": document_id, "sha256": sha256})
        ids = [f"{document_id}:{index}" for index in range(len(chunks))]
        try:
            add_documents(chunks, ids=ids)
            set_document_status(sha256, "completed")
        except Exception:
            set_document_status(sha256, "failed")
            logger.exception("Document ingestion failed for document_id=%s", document_id)
            raise HTTPException(status_code=502, detail="Document ingestion failed") from None
        return {"message": "Document indexed", "file": display_name, "document_id": document_id, "status": "completed", "duplicate": False, "chunks": len(chunks), "ids_created": len(ids)}
    except HTTPException:
        dest.unlink(missing_ok=True)
        raise
    except Exception:
        dest.unlink(missing_ok=True)
        logger.exception("Unexpected document upload failure")
        raise HTTPException(status_code=500, detail="The document could not be processed") from None
    finally:
        await file.close()
