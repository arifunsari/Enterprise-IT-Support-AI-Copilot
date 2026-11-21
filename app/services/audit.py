import json
import sqlite3
import uuid
from datetime import datetime, timezone
from app.core.config import get_settings

settings = get_settings()

def init_db() -> None:
    from pathlib import Path
    Path(settings.audit_db_path).parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(settings.audit_db_path)
    con.execute(
        """CREATE TABLE IF NOT EXISTS query_audit (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            question TEXT NOT NULL,
            source_used TEXT NOT NULL,
            trace_json TEXT NOT NULL
        )"""
    )
    con.execute(
        """CREATE TABLE IF NOT EXISTS ingested_documents (
            sha256 TEXT PRIMARY KEY,
            document_id TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('pending', 'processing', 'completed', 'failed')),
            updated_at TEXT NOT NULL
        )"""
    )
    con.commit()
    con.close()

def write_audit(question: str, source_used: str, trace: list[str]) -> None:
    con = sqlite3.connect(settings.audit_db_path)
    con.execute(
        "INSERT INTO query_audit(created_at, question, source_used, trace_json) VALUES (?, ?, ?, ?)",
        (datetime.now(timezone.utc).isoformat(), question, source_used, json.dumps(trace)),
    )
    con.commit()
    con.close()


def reserve_document(sha256: str) -> tuple[str, str]:
    """Create or reclaim an ingestion record; return (document_id, prior_status)."""
    con = sqlite3.connect(settings.audit_db_path, timeout=10)
    try:
        con.execute("BEGIN IMMEDIATE")
        row = con.execute(
            "SELECT document_id, status FROM ingested_documents WHERE sha256 = ?", (sha256,)
        ).fetchone()
        now = datetime.now(timezone.utc).isoformat()
        if row is None:
            document_id = str(uuid.uuid4())
            con.execute(
                "INSERT INTO ingested_documents VALUES (?, ?, 'pending', ?)",
                (sha256, document_id, now),
            )
            prior_status = "new"
        else:
            document_id, prior_status = row
            if prior_status == "failed":
                con.execute(
                    "UPDATE ingested_documents SET status = 'pending', updated_at = ? WHERE sha256 = ?",
                    (now, sha256),
                )
        con.commit()
        return document_id, prior_status
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def set_document_status(sha256: str, status: str) -> None:
    if status not in {"pending", "processing", "completed", "failed"}:
        raise ValueError("Invalid ingestion status")
    con = sqlite3.connect(settings.audit_db_path, timeout=10)
    try:
        con.execute(
            "UPDATE ingested_documents SET status = ?, updated_at = ? WHERE sha256 = ?",
            (status, datetime.now(timezone.utc).isoformat(), sha256),
        )
        con.commit()
    finally:
        con.close()
