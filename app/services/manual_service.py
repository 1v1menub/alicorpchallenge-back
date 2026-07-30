import json
from functools import lru_cache
from uuid import UUID

from groq import AsyncGroq
from langfuse import observe
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.tracing import langfuse
from app.models import Manual, ManualChunk
from app.schemas.manual import StructuredManual
from app.services import embeddings


@lru_cache
def _groq_client() -> AsyncGroq:
    return AsyncGroq(api_key=settings.groq_api_key)


# ---------------------------------------------------------------------------
# Generation: freeform brief -> StructuredManual (Groq / Llama 3)
# ---------------------------------------------------------------------------

_SCHEMA_BLOCK = """{
  "brand_name": string,
  "summary": string,
  "forbidden_words": string[],
  "color_palette": [{"name": string, "hex": string, "usage": string | null}],
  "sections": [{"title": string, "content": string}]
}"""


def _system_prompt() -> str:
    """Build the manual-generation system prompt (section range is env-driven)."""
    lo = settings.manual_min_sections
    hi = settings.manual_max_sections
    return (
        "Eres un estratega de marca experto. A partir de un brief libre del "
        "usuario, generas un Manual de Marca completo, coherente y accionable.\n\n"
        "Expande e infiere de forma sensata donde el brief no especifique, "
        "manteniendote consistente con lo que si indica. Responde UNICAMENTE con "
        "un objeto JSON valido (sin markdown, sin explicaciones) que siga "
        "EXACTAMENTE este esquema:\n\n"
        + _SCHEMA_BLOCK
        + "\n\nReglas generales:\n"
        "- Todo el contenido en espanol.\n"
        "\nReglas por campo:\n"
        '- "brand_name": si el brief no da un nombre de marca, inventa uno '
        "adecuado.\n"
        '- "summary": 2-3 frases que resuman la esencia de la marca.\n'
        '- "forbidden_words": palabras o expresiones que la marca NO debe usar.\n'
        '- "color_palette": codigos hex reales. La paleta de color va SOLO en '
        'este campo; NO crees una seccion sobre la paleta en "sections".\n'
        f'- "sections": genera entre {lo} y {hi} secciones ENFOCADAS y NO '
        "redundantes, adaptadas a ESTE producto. Enfocate en la IDENTIDAD de "
        "marca: identidad, mision, valores, personalidad, tono y voz, publico "
        "objetivo, mensajes clave, propuesta de valor, e identidad visual "
        "(tipografia, uso del logo, area de proteccion, iconografia, "
        "fotografia, estilo de imagen). Prefiere varias secciones especificas "
        'antes que pocas amplias (p.ej. separa "Tipografia", '
        '"Uso del logo", "Fotografia" en vez de una sola "Identidad visual"). '
        "NO incluyas estrategia ni plan de marketing, ni ejecucion de campanas "
        "(canales, redes sociales, eventos, medicion). Cada seccion cubre una "
        "dimension DISTINTA; no crees dos secciones sobre lo mismo (p.ej. un "
        "solo bloque de reglas de logo). NO rellenes ni repitas solo para "
        "alcanzar el numero.\n"
        "  - Incluye reglas de logo concretas y verificables (tamano minimo, "
        "espacio de proteccion, colocacion) en una seccion visual, para permitir "
        "una auditoria de imagenes posterior.\n"
        "  - Cada seccion: title corto + content detallado y accionable."
    )


@observe(as_type="generation", name="manual-generation", capture_input=False, capture_output=False)
async def generate_structured_manual(brief: str) -> StructuredManual:
    """Turn a freeform brief into a validated StructuredManual via Groq/Llama 3."""
    messages = [
        {"role": "system", "content": _system_prompt()},
        {"role": "user", "content": f"Brief:\n{brief}"},
    ]
    response = await _groq_client().chat.completions.create(
        model=settings.groq_model,
        messages=messages,
        response_format={"type": "json_object"},
        temperature=0.7,
    )
    raw = response.choices[0].message.content or ""
    usage = response.usage
    langfuse.update_current_generation(
        model=settings.groq_model,
        input=messages,
        output=raw,
        usage_details=(
            {"input": usage.prompt_tokens, "output": usage.completion_tokens}
            if usage
            else None
        ),
    )
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Model returned invalid JSON: {exc}") from exc
    return StructuredManual.model_validate(data)


# ---------------------------------------------------------------------------
# Rendering + chunking
# ---------------------------------------------------------------------------


def _render_palette(m: StructuredManual) -> str:
    return ", ".join(
        f"{c.name} {c.hex}" + (f" ({c.usage})" if c.usage else "")
        for c in m.color_palette
    )


def render_manual_text(m: StructuredManual) -> str:
    """Flatten the manual into readable text (UI display + Module III audit)."""
    parts: list[str] = [f"Marca: {m.brand_name}", f"Resumen: {m.summary}"]
    if m.forbidden_words:
        parts.append("Palabras prohibidas: " + ", ".join(m.forbidden_words))
    if m.color_palette:
        parts.append("Paleta de color: " + _render_palette(m))
    for section in m.sections:
        parts.append(f"{section.title}:\n{section.content}")
    return "\n\n".join(parts)


def build_chunks(m: StructuredManual) -> list[tuple[str, str]]:
    """Return (label, text) pairs to embed as RAG chunks.

    One chunk per section (title + content so the heading helps matching), plus a
    synthesized color-palette chunk so image-prompt generation can retrieve it.
    Anchors (brand_name / summary / forbidden_words) are injected directly by the
    consumer, not retrieved, so they are not chunked.
    """
    chunks: list[tuple[str, str]] = [
        (s.title, f"{s.title}\n{s.content}") for s in m.sections
    ]
    if m.color_palette:
        label = "Paleta de color"
        chunks.append((label, f"{label}\n{_render_palette(m)}"))
    return chunks


# ---------------------------------------------------------------------------
# Persistence orchestration (Module I)
# ---------------------------------------------------------------------------


@observe(name="create-manual", capture_input=False, capture_output=False)
async def create_manual(session: AsyncSession, brief: str) -> Manual:
    """Generate -> store manual -> chunk + embed sections -> persist (Module I)."""
    langfuse.update_current_span(input={"brief": brief})
    structured = await generate_structured_manual(brief)

    manual = Manual(
        brief=brief,
        manual=structured.model_dump(mode="json"),
        raw_text=render_manual_text(structured),
    )
    session.add(manual)
    await session.flush()  # assign manual.id before creating child chunks

    chunk_specs = build_chunks(structured)
    if chunk_specs:
        vectors = await embeddings.embed_documents([text for _, text in chunk_specs])
        session.add_all(
            ManualChunk(
                manual_id=manual.id,
                label=label,
                content=text,
                embedding=vector,
            )
            for (label, text), vector in zip(chunk_specs, vectors)
        )

    await session.commit()
    await session.refresh(manual)
    langfuse.update_current_span(
        output={"manual_id": str(manual.id), "manual": structured.model_dump(mode="json")}
    )
    return manual


# ---------------------------------------------------------------------------
# Reads
# ---------------------------------------------------------------------------


async def list_manuals(session: AsyncSession) -> list[Manual]:
    result = await session.execute(select(Manual).order_by(Manual.created_at.desc()))
    return list(result.scalars().all())


async def get_manual(session: AsyncSession, manual_id: UUID) -> Manual | None:
    return await session.get(Manual, manual_id)
