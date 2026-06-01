from __future__ import annotations

from enum import IntEnum
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status

from .config import get_settings


class Role(IntEnum):
    viewer = 1
    engineer = 2
    admin = 3


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing API key",
    )


def _forbidden(required_role: Role) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=f"Insufficient role. Requires at least: {required_role.name}",
    )


def _role_by_api_key(api_key: str) -> Role | None:
    settings = get_settings()

    key_map = {}
    if settings.viewer_api_key:
        key_map[settings.viewer_api_key] = Role.viewer
    if settings.engineer_api_key:
        key_map[settings.engineer_api_key] = Role.engineer
    if settings.admin_api_key:
        key_map[settings.admin_api_key] = Role.admin

    return key_map.get(api_key)


def resolve_role(
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
) -> Role:
    settings = get_settings()
    if not settings.auth_enabled:
        return Role.admin

    if not x_api_key:
        raise _unauthorized()

    role = _role_by_api_key(x_api_key)
    if role is None:
        raise _unauthorized()

    return role


def require_role(required_role: Role):
    def dependency(role: Annotated[Role, Depends(resolve_role)]) -> Role:
        if role < required_role:
            raise _forbidden(required_role)
        return role

    return dependency
