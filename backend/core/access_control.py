"""Shared FastAPI access-control dependencies."""


from typing import TypedDict, cast

from fastapi import Depends, HTTPException

from backend.core.auth import get_current_user
from backend.core.config import is_superadmin


class CurrentUser(TypedDict, total=False):
    id: int
    email: str
    role: str
    tenant_id: int


class SuperAdminUser(CurrentUser):
    pass


def require_superadmin(
    user: CurrentUser = Depends(get_current_user),
) -> SuperAdminUser:
    if not is_superadmin(str(user.get("email") or "")):
        raise HTTPException(status_code=403, detail="Acesso negado: Super Admin apenas")
    return cast(SuperAdminUser, user)
