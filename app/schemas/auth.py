from pydantic import BaseModel, ConfigDict


class TokenData(BaseModel):
    """Decoded JWT claims used across the request lifecycle."""

    model_config = ConfigDict(extra="ignore")  # ignore `exp` and any future claims

    sub: str  # username
    uid: str  # user id
    role: str
    modules: list[str]


class TokenResponse(BaseModel):
    """Returned from /auth/login. `modules` mirrors the JWT for frontend convenience."""

    access_token: str
    token_type: str = "bearer"
    role: str
    modules: list[str]
