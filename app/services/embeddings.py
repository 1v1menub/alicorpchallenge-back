import math
from functools import lru_cache

from google import genai
from google.genai import types
from langfuse import observe

from app.core.config import settings
from app.models.chunk import EMBEDDING_DIM


@lru_cache
def _client() -> genai.Client:
    return genai.Client(api_key=settings.google_api_key)


def _normalize(vector: list[float]) -> list[float]:
    # gemini-embedding-001 only pre-normalizes the full 3072-dim output; for a
    # truncated dimension we L2-normalize ourselves so cosine similarity is sound.
    norm = math.sqrt(sum(x * x for x in vector)) or 1.0
    return [x / norm for x in vector]


@observe(as_type="embedding", name="gemini-embedding", capture_output=False)
async def _embed_batch(texts: list[str], task_type: str) -> list[list[float]]:
    result = await _client().aio.models.embed_content(
        model=settings.gemini_embedding_model,
        contents=texts,
        config=types.EmbedContentConfig(
            output_dimensionality=EMBEDDING_DIM,
            task_type=task_type,
        ),
    )
    return [_normalize(list(e.values)) for e in result.embeddings]


async def embed_documents(texts: list[str]) -> list[list[float]]:
    """Embed several texts for storage/indexing (manual chunks) in one call."""
    return await _embed_batch(texts, "RETRIEVAL_DOCUMENT")


async def embed_document(text: str) -> list[float]:
    """Embed a single text for storage/indexing."""
    return (await _embed_batch([text], "RETRIEVAL_DOCUMENT"))[0]


async def embed_query(text: str) -> list[float]:
    """Embed a retrieval query (used by the Creative Engine, Module II)."""
    return (await _embed_batch([text], "RETRIEVAL_QUERY"))[0]
