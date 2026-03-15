from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from typing import List, Any
import secrets
import json


_DEV_SECRET_KEY = "dev-secret-key-change-in-production"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        env_ignore_empty=True,
    )

    # App
    app_env: str = "development"
    app_name: str = "YouTube Intelligence & Automation OS"
    app_version: str = "1.0.0"
    secret_key: str = _DEV_SECRET_KEY
    allowed_origins: List[str] = ["http://localhost:3000"]
    debug: bool = False

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_allowed_origins(cls, v: Any) -> Any:
        if isinstance(v, str):
            v = v.strip()
            if not v:
                return ["http://localhost:3000"]
            if v.startswith("["):
                return json.loads(v)
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        if v == _DEV_SECRET_KEY:
            import os
            if os.environ.get("APP_ENV", "development") == "production":
                raise ValueError(
                    "SECRET_KEY must be set to a secure random value in production. "
                    f"Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
                )
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long")
        return v

    # Database
    database_url: str = "postgresql+asyncpg://ytautos:password@localhost:5432/ytautos_db"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # OpenAI
    openai_api_key: str = ""
    openai_org_id: str = ""
    openai_model_premium: str = "gpt-4o"
    openai_model_fast: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-large"

    # Anthropic
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-6"

    # ElevenLabs
    elevenlabs_api_key: str = ""
    elevenlabs_voice_id_default: str = "21m00Tcm4TlvDq8ikWAM"

    # YouTube
    youtube_api_key: str = ""
    youtube_client_id: str = ""
    youtube_client_secret: str = ""
    youtube_daily_api_quota: int = 10_000

    # Cloudflare R2
    r2_access_key_id: str = ""
    r2_secret_access_key: str = ""
    r2_bucket_name: str = "ytautos-assets"
    r2_endpoint_url: str = ""

    # Langfuse
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "https://cloud.langfuse.com"

    # Video Generation
    kling_api_key: str = ""
    runway_api_key: str = ""

    # Stock Asset APIs
    pexels_api_key: str = ""
    pixabay_api_key: str = ""

    # Quality Gate Thresholds
    min_niche_score: int = 70
    min_hook_score: float = 8.0
    min_naturalness_score: float = 8.0
    min_originality_score: int = 85
    min_seo_score: int = 75
    max_similarity_cosine: float = 0.85

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


settings = Settings()
