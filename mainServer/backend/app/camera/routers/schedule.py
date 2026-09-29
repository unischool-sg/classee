from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field, model_validator

from camera.auth import verify_token
from common.schedule import get_schedule

router = APIRouter()


class ScheduleRequest(BaseModel):
    start_at: int = Field(ge=0)
    end_at: int = Field(ge=0)

    @model_validator(mode="after")
    def check_range(self):
        if self.end_at <= self.start_at:
            raise ValueError("end_at must be greater than start_at")
        return self


class Plan(BaseModel):
    classId: int
    start_at: int
    end_at: int


@router.post("/api/schedule", response_model=list[Plan])
async def schedule(
    body: ScheduleRequest,
    token: Annotated[str, Depends(verify_token)],
):
    try:
        return await run_in_threadpool(get_schedule, token, body.start_at, body.end_at)
    except PermissionError as e:
        raise HTTPException(status.HTTP_403_FORBIDDEN, str(e)) from e
