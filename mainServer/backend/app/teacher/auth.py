import hashlib
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.concurrency import run_in_threadpool
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from common.db import conn, get_session_user_id

bearer = HTTPBearer()


def _lookup_user_id(token: str) -> int | None:
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    with conn:
        return get_session_user_id(conn, token_hash)


async def verify_session(credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer)]) -> int:
    user_id = await run_in_threadpool(_lookup_user_id, credentials.credentials)
    if user_id is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired session")
    return user_id
