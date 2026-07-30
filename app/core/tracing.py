from langfuse import Langfuse

from app.core.config import settings

# Global Langfuse client. The @observe() decorators discover it automatically.
# Tracing is a no-op when keys are absent (e.g. local runs without Langfuse).
langfuse = Langfuse(
    public_key=settings.langfuse_public_key or "",
    secret_key=settings.langfuse_secret_key or "",
    base_url=settings.langfuse_base_url,
    tracing_enabled=bool(settings.langfuse_public_key and settings.langfuse_secret_key),
)
