from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # =========================================================================
    # Database Configuration
    # =========================================================================
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_HOST: str
    POSTGRES_PORT: int

    # =========================================================================
    # LLM Configuration
    # =========================================================================
    OPENAI_API_KEY: str
    OPENAI_API_BASE: str = "https://api.openai.com/v1"
    OPENAI_MODEL_NAME: str = "gpt-4o"

    # =========================================================================
    # GCP Core Configuration
    # =========================================================================
    GCP_PROJECT_ID: Optional[str] = None
    GCP_REGION: str = "europe-west9"
    BACKEND_URL: Optional[str] = None  # For Cloud Tasks callbacks
    BACKEND_SA_EMAIL: Optional[str] = None  # Service account for OIDC

    # =========================================================================
    # Cloud Tasks (Async Resilience)
    # =========================================================================
    CLOUD_TASKS_ENABLED: bool = False
    CLOUD_TASKS_QUEUE: str = "awp-agent-actions"

    # =========================================================================
    # Sensitive Data Protection (Cloud DLP)
    # =========================================================================
    SDP_ENABLED: bool = False
    SDP_INSPECT_TEMPLATE: Optional[str] = None
    SDP_DEIDENTIFY_TEMPLATE: Optional[str] = None

    # =========================================================================
    # Vertex AI RAG Engine
    # =========================================================================
    VERTEX_RAG_CORPUS: Optional[str] = None
    VERTEX_EMBEDDING_MODEL: str = "text-embedding-005"
    VERTEX_SEARCH_ENGINE: Optional[str] = None

    # =========================================================================
    # BigQuery (Structured Data)
    # =========================================================================
    BIGQUERY_DATASET: Optional[str] = None
    BIGQUERY_MAX_BYTES_BILLED: int = 1_000_000_000  # 1GB default

    # =========================================================================
    # Cloud Logging & Observability
    # =========================================================================
    CLOUD_LOGGING_ENABLED: bool = False
    CLOUD_TRACE_ENABLED: bool = False

    # =========================================================================
    # Computed Properties
    # =========================================================================

    @property
    def is_gcp_environment(self) -> bool:
        """Check if running in GCP with project configured."""
        return self.GCP_PROJECT_ID is not None

    @property
    def database_url(self) -> str:
        """Construct PostgreSQL connection string."""
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def async_database_url(self) -> str:
        """Construct async PostgreSQL connection string."""
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
