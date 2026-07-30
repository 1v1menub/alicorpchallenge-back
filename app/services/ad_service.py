from collections.abc import Sequence
from functools import lru_cache
from uuid import UUID

from groq import AsyncGroq
from langfuse import observe
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.tracing import langfuse
from app.models import Manual, ManualChunk, ProductAd
from app.models.enums import AdStatus, AdType
from app.schemas.manual import StructuredManual
from app.services import embeddings


@lru_cache
def _groq_client() -> AsyncGroq:
    return AsyncGroq(api_key=settings.groq_api_key)


# ---------------------------------------------------------------------------
# Generation: ad content grounded in brand anchors + retrieved chunks (Groq)
# ---------------------------------------------------------------------------

AD_SYSTEM_PROMPT = """Eres un redactor creativo experto que trabaja para una marca. \
Generas contenido creativo fiel a la identidad de la marca, siguiendo ESTRICTAMENTE \
las reglas proporcionadas. NUNCA uses las palabras prohibidas. Responde unicamente \
con el contenido solicitado, en espanol, sin explicaciones ni markdown."""

AD_TYPE_INSTRUCTIONS = {
    AdType.product_description: (
        "una descripcion de producto persuasiva y fiel a la marca (2 a 4 frases)."
    ),
    AdType.video_script: (
        "un guion breve para un video publicitario, con actores y sus lineas, "
        "indicaciones de escena y lineas de narracion en caso de que sea "
        "necesario un narrador."
    ),
    AdType.image_prompt: (
        "un prompt detallado para un generador de imagenes: describe sujeto, "
        "composicion, colores, iluminacion y estilo visual, respetando la "
        "identidad visual y las reglas de logo de la marca."
    ),
}


@observe(as_type="generation", name="ad-generation", capture_input=False, capture_output=False)
async def generate_ad(
    ad_type: AdType,
    brief: str,
    manual: StructuredManual,
    chunks: Sequence[ManualChunk],
) -> str:
    """Generate ad content grounded in brand anchors + retrieved manual chunks."""
    anchors = [f"Marca: {manual.brand_name}", f"Resumen: {manual.summary}"]
    if manual.forbidden_words:
        anchors.append(
            "PALABRAS PROHIBIDAS (nunca usar): " + ", ".join(manual.forbidden_words)
        )
    if manual.color_palette:
        anchors.append(
            "Paleta de color: "
            + ", ".join(f"{c.name} {c.hex}" for c in manual.color_palette)
        )
    anchors_text = "\n".join(anchors)
    retrieved = "\n\n".join(f"[{c.label}]\n{c.content}" for c in chunks)
    brief_line = (
        f"Brief del anuncio: {brief}"
        if brief.strip()
        else "Brief del anuncio: (no especificado; genera una pieza "
        "representativa y fiel a la marca)"
    )

    user_prompt = f"""Reglas de marca (ancla, siempre validas):
{anchors_text}

Contexto relevante del manual (recuperado para este encargo):
{retrieved or "(sin secciones adicionales)"}

Encargo: genera {AD_TYPE_INSTRUCTIONS[ad_type]}
{brief_line}"""

    messages = [
        {"role": "system", "content": AD_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]
    response = await _groq_client().chat.completions.create(
        model=settings.groq_model,
        messages=messages,
        temperature=0.8,
    )
    content = (response.choices[0].message.content or "").strip()
    usage = response.usage
    langfuse.update_current_generation(
        model=settings.groq_model,
        input=messages,
        output=content,
        usage_details=(
            {"input": usage.prompt_tokens, "output": usage.completion_tokens}
            if usage
            else None
        ),
    )
    return content


# ---------------------------------------------------------------------------
# Retrieval + persistence orchestration (Module II)
# ---------------------------------------------------------------------------

# Per-type seed that biases retrieval toward the dimensions that matter for it.
QUERY_SEEDS: dict[AdType, str] = {
    AdType.product_description: "tono, voz, lenguaje, mensajes clave, publico",
    AdType.video_script: "tono, mensajes clave, frases de ejemplo, publico",
    AdType.image_prompt: (
        "identidad visual, paleta de color, reglas de logo, estilo de imagen, fotografia"
    ),
}


@observe(as_type="retriever", name="retrieve-chunks", capture_input=False, capture_output=False)
async def _retrieve_chunks(
    session: AsyncSession, manual_id: UUID, query_vec: list[float], k: int
) -> list[ManualChunk]:
    """Top-k manual chunks nearest the query vector (pgvector cosine), one manual.

    Rank-based (top-k), not an absolute threshold: within a single manual the
    similarity scores cluster tightly, so a fixed cutoff is brittle.
    """
    stmt = (
        select(ManualChunk)
        .where(ManualChunk.manual_id == manual_id)
        .order_by(ManualChunk.embedding.cosine_distance(query_vec))
        .limit(k)
    )
    result = await session.execute(stmt)
    chunks = list(result.scalars().all())
    langfuse.update_current_span(
        input={"k": k},
        output=[{"label": c.label, "content": c.content} for c in chunks],
    )
    return chunks


@observe(name="create-ad", capture_input=False, capture_output=False)
async def create_ad(
    session: AsyncSession,
    manual_id: UUID,
    ad_type: AdType,
    brief: str | None = None,
) -> ProductAd | None:
    """Module II — RAG-grounded ad generation. Returns None if the manual is missing."""
    langfuse.update_current_span(
        input={"manual_id": str(manual_id), "ad_type": ad_type.value, "brief": brief}
    )
    manual = await session.get(Manual, manual_id)
    if manual is None:
        langfuse.update_current_span(output="manual not found", level="WARNING")
        return None

    structured = StructuredManual.model_validate(manual.manual)
    brief_text = (brief or "").strip()

    # Retrieve the most relevant sections of THIS manual. The per-type seed always
    # applies; the creator's brief refines the query when provided.
    query = QUERY_SEEDS[ad_type]
    if brief_text:
        query = f"{QUERY_SEEDS[ad_type]}. {brief_text}"
    query_vec = await embeddings.embed_query(query)
    chunks = await _retrieve_chunks(session, manual_id, query_vec, settings.rag_top_k)

    content = await generate_ad(ad_type, brief_text, structured, chunks)

    ad = ProductAd(manual_id=manual_id, ad_type=ad_type, content=content)
    session.add(ad)
    await session.commit()
    await session.refresh(ad)
    langfuse.update_current_span(
        output={"ad_id": str(ad.id), "ad_type": ad_type.value, "content": content}
    )
    return ad


# ---------------------------------------------------------------------------
# Reads
# ---------------------------------------------------------------------------


async def list_ads(
    session: AsyncSession,
    manual_id: UUID | None = None,
    ad_type: AdType | None = None,
    status: AdStatus | None = None,
) -> list[ProductAd]:
    stmt = select(ProductAd)
    if manual_id is not None:
        stmt = stmt.where(ProductAd.manual_id == manual_id)
    if ad_type is not None:
        stmt = stmt.where(ProductAd.ad_type == ad_type)
    if status is not None:
        stmt = stmt.where(ProductAd.status == status)
    result = await session.execute(stmt.order_by(ProductAd.created_at.desc()))
    return list(result.scalars().all())


async def get_ad(session: AsyncSession, ad_id: UUID) -> ProductAd | None:
    return await session.get(ProductAd, ad_id)
