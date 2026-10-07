from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field, model_validator

from common.db import (
    ConflictError,
    add_confirmed_slot,
    add_draft_slots,
    cancel_confirmed_slots,
    confirm_month,
    delete_draft_slots,
    edit_confirmed_slots,
    edit_draft_slots,
    fetch_templates,
    get_confirmed_months,
    get_confirmed_slots,
    get_draft_slots,
    is_month_confirmed,
    read,
    replace_templates,
)
from common.models import DraftSlot, ScheduleMonth, SessionUser, Slot, TemplatePeriod
from common.schedule import create_month_schedule
from teacher.auth import verify_session
from teacher.tx import as_user, run

router = APIRouter()


class RangeRequest(BaseModel):
    classroom_id: int = Field(ge=0)
    start_at: datetime
    end_at: datetime

    @model_validator(mode="after")
    def check_range(self):
        if self.end_at <= self.start_at:
            raise ValueError("end_at must be greater than start_at")
        return self


class DraftAddRequest(BaseModel):
    classroom_id: int = Field(ge=0)
    slots: list[Slot] = Field(min_length=1)


class SlotsRequest(BaseModel):
    slots: list[DraftSlot] = Field(min_length=1)


class ClassroomRequest(BaseModel):
    classroom_id: int = Field(ge=0)


class MonthRequest(BaseModel):
    classroom_id: int = Field(ge=0)
    year: int = Field(ge=2000, le=2100)
    month: int = Field(ge=1, le=12)


class TemplatesSetRequest(BaseModel):
    classroom_id: int = Field(ge=0)
    periods: list[TemplatePeriod]


class ConfirmedAddRequest(BaseModel):
    classroom_id: int = Field(ge=0)
    slot: Slot


def _generate_draft(conn, classroom_id: int, year: int, month: int, user_id: int) -> int:
    if is_month_confirmed(conn, classroom_id, year, month):
        raise ConflictError(f"{year}-{month:02d} is already confirmed")
    slots = list(create_month_schedule(fetch_templates(conn, classroom_id), year, month))
    add_draft_slots(conn, classroom_id, slots, user_id)
    return len(slots)


@router.post("/api/schedule-draft/get", response_model=list[DraftSlot])
async def get_draft(
    body: RangeRequest,
    user: Annotated[SessionUser, Depends(verify_session)],
):
    return await run(read(), get_draft_slots, body.classroom_id, body.start_at, body.end_at)


@router.post("/api/schedule-draft/add", status_code=status.HTTP_201_CREATED)
async def add_draft(
    body: DraftAddRequest,
    user: Annotated[SessionUser, Depends(verify_session)],
):
    await run(as_user(user.id), add_draft_slots, body.classroom_id, body.slots, user.id)
    return {"added": len(body.slots)}


@router.post("/api/schedule-draft/edit")
async def edit_draft(
    body: SlotsRequest,
    user: Annotated[SessionUser, Depends(verify_session)],
):
    await run(as_user(user.id), edit_draft_slots, body.slots)
    return {"edited": len(body.slots)}


@router.post("/api/schedule-draft/delete")
async def delete_draft(
    body: SlotsRequest,
    user: Annotated[SessionUser, Depends(verify_session)],
):
    await run(as_user(user.id), delete_draft_slots, body.slots)
    return {"deleted": len(body.slots)}


@router.post("/api/schedule-draft/generate", status_code=status.HTTP_201_CREATED)
async def generate_draft(
    body: MonthRequest,
    user: Annotated[SessionUser, Depends(verify_session)],
):
    added = await run(as_user(user.id), _generate_draft, body.classroom_id, body.year, body.month, user.id)
    return {"added": added}


@router.post("/api/period-templates/get", response_model=list[TemplatePeriod])
async def get_templates(
    body: ClassroomRequest,
    user: Annotated[SessionUser, Depends(verify_session)],
):
    return await run(read(), fetch_templates, body.classroom_id)


@router.post("/api/period-templates/set")
async def set_templates(
    body: TemplatesSetRequest,
    user: Annotated[SessionUser, Depends(verify_session)],
):
    await run(as_user(user.id), replace_templates, body.classroom_id, body.periods)
    return {"periods": len(body.periods)}


@router.post("/api/schedule-months/get", response_model=list[ScheduleMonth])
async def get_months(
    body: ClassroomRequest,
    user: Annotated[SessionUser, Depends(verify_session)],
):
    return await run(read(), get_confirmed_months, body.classroom_id)


@router.post("/api/schedule-months/confirm")
async def confirm(
    body: MonthRequest,
    user: Annotated[SessionUser, Depends(verify_session)],
):
    confirmed = await run(as_user(user.id), confirm_month, body.classroom_id, body.year, body.month, user.id)
    return {"confirmed": confirmed}


@router.post("/api/schedule/get", response_model=list[DraftSlot])
async def get_confirmed(
    body: RangeRequest,
    user: Annotated[SessionUser, Depends(verify_session)],
):
    return await run(read(), get_confirmed_slots, body.classroom_id, body.start_at, body.end_at)


@router.post("/api/schedule/add", status_code=status.HTTP_201_CREATED)
async def add_confirmed(
    body: ConfirmedAddRequest,
    user: Annotated[SessionUser, Depends(verify_session)],
):
    slot_id = await run(as_user(user.id), add_confirmed_slot, body.classroom_id, body.slot, user.id)
    return {"id": slot_id}


@router.post("/api/schedule/edit")
async def edit_confirmed(
    body: SlotsRequest,
    user: Annotated[SessionUser, Depends(verify_session)],
):
    await run(as_user(user.id), edit_confirmed_slots, body.slots)
    return {"edited": len(body.slots)}


@router.post("/api/schedule/cancel")
async def cancel_confirmed(
    body: SlotsRequest,
    user: Annotated[SessionUser, Depends(verify_session)],
):
    await run(as_user(user.id), cancel_confirmed_slots, body.slots, user.id)
    return {"cancelled": len(body.slots)}
