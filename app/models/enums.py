import enum


class AdType(str, enum.Enum):
    """The kind of creative content the Creative Engine produces."""

    image_prompt = "image_prompt"
    video_script = "video_script"
    product_description = "product_description"


class AdStatus(str, enum.Enum):
    """Governance state machine: pending -> approved | rejected."""

    pending = "pending"
    approved = "approved"
    rejected = "rejected"
