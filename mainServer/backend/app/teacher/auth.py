from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, status
from fastapi.concurrency import run_in_threadpool

from common.db import get_session_user, read
from common.models import SessionUser
from common.security import hash_token

SESSION_COOKIE = "session"


def _lookup_user(token: str) -> SessionUser | None:
    with read() as conn:
        return get_session_user(conn, hash_token(token))


async def verify_session(session: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None) -> SessionUser:
    user = await run_in_threadpool(_lookup_user, session) if session else None
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired session")
    return user


async def require_admin(user: Annotated[SessionUser, Depends(verify_session)]) -> SessionUser:
    if not user.is_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin only")
    return user


async def require_recording_viewer(user: Annotated[SessionUser, Depends(verify_session)]) -> SessionUser:
    if not user.can_view_recordings:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not allowed to view recordings")
    return user
