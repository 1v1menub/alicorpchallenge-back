from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import ValidationError

from app.core.modules import ModuleKey
from app.core.security import decode_access_token
from app.schemas.auth import TokenData

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]) -> TokenData:
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
        return TokenData(**payload)
    except (jwt.PyJWTError, ValidationError):
        raise credentials_exc


CurrentUser = Annotated[TokenData, Depends(get_current_user)]


def require_module(module: ModuleKey):
    """Dependency factory: 403 unless the caller's JWT grants `module`."""

    async def _checker(current_user: CurrentUser) -> TokenData:
        if module.value not in current_user.modules:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required module access: {module.value}",
            )
        return current_user

    return _checker
