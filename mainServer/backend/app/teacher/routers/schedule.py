from collections.abc import Callable
from contextlib import AbstractContextManager
from datetime import datetime
from typing import Annotated

import psycopg2
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field, model_validator

from common.db import (
    add_draft_slots,
    delete_draft_slots,
    edit_draft_slots,
    get_draft_slots,
    read,
    write,
)
from common.models import DraftSlot, Slot
from teacher.auth import verify_session

router = APIRouter()


class DraftGetRequest(BaseModel):
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


class DraftEditRequest(BaseModel):
    slots: list[DraftSlot] = Field(min_length=1)


class DraftDeleteRequest(BaseModel):
    slots: list[DraftSlot] = Field(min_length=1)


def _in_transaction(tx: AbstractContextManager, func: Callable, *args):
    with tx as conn:
        return func(conn, *args)


async def _run(tx: AbstractContextManager, func: Callable, *args):
    try:
        return await run_in_threadpool(_in_transaction, tx, func, *args)
    except ValueError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e)) from e
    except psycopg2.IntegrityError as e:
        raise HTTPException(status.HTTP_409_CONFLICT, e.pgerror or str(e)) from e


@router.post("/api/schedule-draft/get", response_model=list[DraftSlot])
async def get_draft(
    body: DraftGetRequest,
    user_id: Annotated[int, Depends(verify_session)],
):
    return await _run(read(), get_draft_slots, body.classroom_id, body.start_at, body.end_at)


@router.post("/api/schedule-draft/add", status_code=status.HTTP_201_CREATED)
async def add_draft(
    body: DraftAddRequest,
    user_id: Annotated[int, Depends(verify_session)],
):
    await _run(write("app.user_id", str(user_id)), add_draft_slots, body.classroom_id, body.slots, user_id)
    return {"added": len(body.slots)}


@router.post("/api/schedule-draft/edit")
async def edit_draft(
    body: DraftEditRequest,
    user_id: Annotated[int, Depends(verify_session)],
):
    await _run(write("app.user_id", str(user_id)), edit_draft_slots, body.slots)
    return {"edited": len(body.slots)}


@router.post("/api/schedule-draft/delete")
async def delete_draft(
    body: DraftDeleteRequest,
    user_id: Annotated[int, Depends(verify_session)],
):
    await _run(write("app.user_id", str(user_id)), delete_draft_slots, body.slots)
    return {"deleted": len(body.slots)}
