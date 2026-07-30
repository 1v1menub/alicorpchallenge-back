from functools import lru_cache

from google import genai
from google.genai import types
from langfuse import observe

from app.core.config import settings
from app.core.tracing import langfuse
from app.schemas.ad import AuditResponse

AUDIT_SYSTEM_PROMPT = (
    "Eres un auditor de identidad de marca. Recibes el Manual de Marca (texto) y "
    "una imagen candidata. Evalua si la imagen CUMPLE las reglas del manual, "
    "prestando especial atencion a la identidad visual: paleta de color, reglas y "
    "tamano del logo, tipografia, estilo de imagen y fotografia. Responde en "
    "espanol. Si cumple, passed=true con un feedback breve de por que cumple. Si "
    "NO cumple, passed=false y explica exactamente que regla(s) del manual "
    "incumple (por ejemplo: 'el logo es demasiado pequeno segun las reglas del "
    "manual')."
)


@lru_cache
def _client() -> genai.Client:
    return genai.Client(api_key=settings.google_api_key)


@observe(as_type="generation", name="vision-audit", capture_input=False, capture_output=False)
async def audit_image(
    manual_text: str, image_bytes: bytes, mime_type: str
) -> AuditResponse:
    """Contrast an image against the brand manual using Gemini vision."""
    response = await _client().aio.models.generate_content(
        model=settings.gemini_vision_model,
        contents=[
            types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
            f"Manual de Marca:\n{manual_text}\n\n"
            "Audita la imagen candidata contra este manual y responde el veredicto.",
        ],
        config=types.GenerateContentConfig(
            system_instruction=AUDIT_SYSTEM_PROMPT,
            response_mime_type="application/json",
            response_schema=AuditResponse,
        ),
    )
    verdict = response.parsed
    if not isinstance(verdict, AuditResponse):
        # Fallback if the SDK returned a dict / raw text instead of the model.
        import json

        verdict = AuditResponse.model_validate(json.loads(response.text or "{}"))
    langfuse.update_current_generation(
        model=settings.gemini_vision_model,
        input=f"[imagen {mime_type}] + Manual de Marca:\n{manual_text}",
        output=verdict.model_dump(),
    )
    return verdict
