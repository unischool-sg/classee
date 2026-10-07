from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from common.db import add_device, get_devices, read, revoke_device
from common.models import DeviceInfo, SessionUser
from common.security import gen_camera_token, hash_token
from teacher.auth import require_admin
from teacher.tx import as_user, run

router = APIRouter()


class DeviceAddRequest(BaseModel):
    classroom_id: int = Field(ge=0)
    name: str = Field(min_length=1, max_length=100)


class DeviceRevokeRequest(BaseModel):
    id: int = Field(ge=0)


@router.post("/api/devices/get", response_model=list[DeviceInfo])
async def get(user: Annotated[SessionUser, Depends(require_admin)]):
    return await run(read(), get_devices)


@router.post("/api/devices/add", status_code=status.HTTP_201_CREATED)
async def add(
    body: DeviceAddRequest,
    user: Annotated[SessionUser, Depends(require_admin)],
):
    # トークンはここで1回だけ返し、DB にはハッシュしか残さない。
    token = gen_camera_token()
    device_id = await run(as_user(user.id), add_device, body.classroom_id, body.name, hash_token(token))
    return {"id": device_id, "token": token}


@router.post("/api/devices/revoke")
async def revoke(
    body: DeviceRevokeRequest,
    user: Annotated[SessionUser, Depends(require_admin)],
):
    await run(as_user(user.id), revoke_device, body.id)
    return {"revoked": body.id}
