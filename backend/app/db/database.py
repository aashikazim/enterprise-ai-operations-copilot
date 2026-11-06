from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, SecretStr, field_validator
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


class Settings(BaseSettings):
    #database 
    database_url: str
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # smtp
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 465
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from_email: str = ""
    invitation_base_url: str = (
        "http://localhost:5173/accept-invitation"
    )

    #opeanai
    openai_api_key: str = ""
    openai_model: str = "gpt-4.1-mini"

    rag_eval_enabled: bool = False
    rag_eval_sample_rate: float = Field(default=0.0, ge=0, le=1, allow_inf_nan=False)
    monitoring_metrics_token: SecretStr = SecretStr("")
    tracing_enabled: bool = False
    otel_exporter_otlp_traces_endpoint: str = ""
    evaluation_worker_concurrency: int = Field(1, ge=1, le=8)
    evaluation_lease_seconds: int = Field(600, ge=30, le=3600)
    slack_tenant_credentials: SecretStr = SecretStr("{}")

    @field_validator("rag_eval_enabled", "tracing_enabled", mode="before")
    @classmethod
    def validate_eval_enabled(cls, value):
        if isinstance(value, bool):
            return value
        if isinstance(value, str) and value.lower() in {"true", "false"}:
            return value.lower() == "true"
        raise ValueError("RAG_EVAL_ENABLED must be true or false")

    @field_validator("rag_eval_sample_rate", mode="before")
    @classmethod
    def validate_eval_rate(cls, value):
        if isinstance(value, bool):
            raise ValueError("RAG_EVAL_SAMPLE_RATE must be numeric, not boolean")
        return value

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


@lru_cache
def get_settings():
    return Settings()


engine = create_engine(
    get_settings().database_url,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
