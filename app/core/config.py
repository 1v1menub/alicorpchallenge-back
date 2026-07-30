from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings, loaded from environment / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # --- database (any Postgres; use the asyncpg driver) ---
    database_url: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/content_suite"
    )

    # --- auth / jwt ---
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 12  # 12h

    # default password for the seeded role users (Credenciales de Acceso)
    seed_password: str = "password123"

    # --- CORS (JSON array in env, e.g. ["http://localhost:5173"]) ---
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
    ]

    # --- AI providers ---
    google_api_key: str | None = None
    groq_api_key: str | None = None
    langfuse_public_key: str | None = None
    langfuse_secret_key: str | None = None
    langfuse_base_url: str | None = None

    # --- model selection ---
    groq_model: str = "llama-3.3-70b-versatile"  # text generation
    gemini_embedding_model: str = "gemini-embedding-001"  # RAG embeddings (768-dim)
    gemini_vision_model: str = "gemini-flash-latest"  # multimodal audit (Module III)

    # --- RAG retrieval ---
    rag_top_k: int = 8  # how many manual chunks to retrieve per ad generation

    # --- manual generation ---
    manual_min_sections: int = 12  # soft floor on generated manual sections
    manual_max_sections: int = 20  # soft ceiling on generated manual sections

    # --- Supabase Storage (Module III image assets) ---
    supabase_url: str | None = None
    supabase_service_key: str | None = None
    supabase_storage_bucket: str = "ad-images"


settings = Settings()
