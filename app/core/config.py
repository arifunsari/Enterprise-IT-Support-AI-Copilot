from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import model_validator

BASE_DIR = Path(__file__).resolve().parents[2]

class Settings(BaseSettings):
    app_name: str = "Enterprise IT Support Agentic RAG Copilot"
    app_env: str = "development"
    openai_api_key: str = ""
    tavily_api_key: str = ""
    pinecone_api_key: str = ""
    pinecone_index_name: str = "industry-agentic-rag-kb-v2"
    pinecone_namespace: str = "langgraph-agentic-rag"
    embedding_model: str = "text-embedding-3-small"
    openai_model: str = "gpt-4o-mini"
    top_k: int = 4
    max_retries: int = 1
    admin_api_key: str = ""
    max_upload_size_bytes: int = 10 * 1024 * 1024
    hybrid_retrieval_enabled: bool = True
    retrieval_candidate_k: int = 12
    langfuse_enabled: bool = False
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_base_url: str = ""
    audit_db_path: str = str(BASE_DIR / "data" / "audit.db")  # SQL database path for audit logs
    upload_dir: str = str(BASE_DIR / "uploads")
    sample_kb_dir: str = str(BASE_DIR / "data" / "sample_kb")

    model_config = SettingsConfigDict(env_file=str(BASE_DIR / ".env"), extra="ignore")

    @model_validator(mode="after")
    def require_production_admin_key(self):
        if self.app_env.strip().lower() in {"prod", "production"} and len(self.admin_api_key) < 32:
            raise ValueError("ADMIN_API_KEY must be configured with at least 32 characters in production")
        if self.max_upload_size_bytes <= 0:
            raise ValueError("MAX_UPLOAD_SIZE_BYTES must be greater than zero")
        if self.retrieval_candidate_k < self.top_k:
            raise ValueError("RETRIEVAL_CANDIDATE_K must be greater than or equal to TOP_K")
        return self




@lru_cache
def get_settings() -> Settings:
    return Settings()
