from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field, model_validator

from camera.auth import verify_device
from common.db import get_device_plans, touch_device, write
from common.models import Device, Plan

router = APIRouter()


class ScheduleRequest(BaseModel):
    start_at: int = Field(ge=0)
    end_at: int = Field(ge=0)

    @model_validator(mode="after")
    def check_range(self):
        if self.end_at <= self.start_at:
            raise ValueError("end_at must be greater than start_at")
        return self


def _get_schedule(device: Device, start_at: int, end_at: int) -> list[Plan]:
    with write("app.device_id", str(device.id)) as conn:
        touch_device(conn, device.id)
        return get_device_plans(conn, device, start_at, end_at)


@router.post("/api/schedule", response_model=list[Plan])
async def schedule(
    body: ScheduleRequest,
    device: Annotated[Device, Depends(verify_device)],
):
    return await run_in_threadpool(_get_schedule, device, body.start_at, body.end_at)
