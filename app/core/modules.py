import enum


class ModuleKey(str, enum.Enum):
    """Canonical module identifiers. Embedded in the JWT and checked per-endpoint."""

    brand_dna = "brand_dna"
    creative_engine = "creative_engine"
    image_audit = "image_audit"
    non_image_audit = "non_image_audit"
    observability = "observability"


class RoleName(str, enum.Enum):
    creador = "Creador"
    aprobador_a = "Aprobador A"
    aprobador_b = "Aprobador B"
    admin = "Admin"


# Human-readable labels stored on the modules table.
MODULE_LABELS: dict[ModuleKey, str] = {
    ModuleKey.brand_dna: "Brand DNA Architect",
    ModuleKey.creative_engine: "Creative Engine",
    ModuleKey.image_audit: "Image Audit",
    ModuleKey.non_image_audit: "Non-Image Audit",
    ModuleKey.observability: "Observability",
}

# Which modules each role gets (the many-to-many seed data).
ROLE_MODULES: dict[RoleName, list[ModuleKey]] = {
    RoleName.creador: [
        ModuleKey.brand_dna,
        ModuleKey.creative_engine,
        ModuleKey.observability,
    ],
    RoleName.aprobador_a: [
        ModuleKey.non_image_audit,
        ModuleKey.observability,
    ],
    RoleName.aprobador_b: [
        ModuleKey.image_audit,
        ModuleKey.observability,
    ],
    RoleName.admin: list(ModuleKey),  # full access to every module
}

# Default username seeded for each role.
SEED_USERNAMES: dict[RoleName, str] = {
    RoleName.creador: "creador",
    RoleName.aprobador_a: "aprobador_a",
    RoleName.aprobador_b: "aprobador_b",
    RoleName.admin: "admin",
}
