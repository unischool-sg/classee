from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.concurrency import run_in_threadpool
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from common.db import get_device_by_token_hash, read, touch_device, write
from common.models import Device
from common.security import hash_token

bearer = HTTPBearer()


def _lookup_device(token: str) -> Device | None:
    with read() as conn:
        device = get_device_by_token_hash(conn, hash_token(token))
    if device is None:
        return None
    with write("app.device_id", str(device.id)) as conn:
        touch_device(conn, device.id)
    return device


async def verify_device(credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer)]) -> Device:
    device = await run_in_threadpool(_lookup_device, credentials.credentials)
    if device is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or revoked device token")
    return device
