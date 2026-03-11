from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    app_env: str = "development"
    app_name: str = "YouTube Intelligence & Automation OS"
    app_version: str = "1.0.0"
    secret_key: str = "dev-secret-key-change-in-production"
    allowed_origins: List[str] = ["http://localhost:3000"]
    debug: bool = True

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
