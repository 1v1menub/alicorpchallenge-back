from app.schemas.ad import (
    AdCreateRequest,
    AdResponse,
    AuditResponse,
    StatusUpdateRequest,
)
from app.schemas.manual import (
    ColorSpec,
    ManualCreateRequest,
    ManualResponse,
    StructuredManual,
)

__all__ = [
    # manual
    "ColorSpec",
    "StructuredManual",
    "ManualCreateRequest",
    "ManualResponse",
    # ad
    "AdCreateRequest",
    "AdResponse",
    "AuditResponse",
    "StatusUpdateRequest",
]
