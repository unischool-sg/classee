import hashlib
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.concurrency import run_in_threadpool
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from common.db import get_device_by_token_hash, transaction
from common.models import Device

bearer = HTTPBearer()


def _lookup_device(token: str) -> Device | None:
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    with transaction() as conn:
        return get_device_by_token_hash(conn, token_hash)


async def verify_device(credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer)]) -> Device:
    device = await run_in_threadpool(_lookup_device, credentials.credentials)
    if device is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or revoked device token")
    return device
