from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator

from common.db import add_user, disable_user, edit_user, get_users, read
from common.models import SessionUser, User
from teacher.auth import require_admin
from teacher.tx import as_user, run

router = APIRouter()


class UserAddRequest(BaseModel):
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+$")
    is_admin: bool = False
    can_view_recordings: bool = False

    @field_validator("email")
    @classmethod
    def lower_email(cls, v: str) -> str:
        return v.lower()


class UserEditRequest(BaseModel):
    id: int = Field(ge=0)
    is_admin: bool
    can_view_recordings: bool


class UserDisableRequest(BaseModel):
    id: int = Field(ge=0)


@router.post("/api/users/get", response_model=list[User])
async def get(user: Annotated[SessionUser, Depends(require_admin)]):
    return await run(read(), get_users)


@router.post("/api/users/add", status_code=status.HTTP_201_CREATED)
async def add(
    body: UserAddRequest,
    user: Annotated[SessionUser, Depends(require_admin)],
):
    user_id = await run(as_user(user.id), add_user, body.email, body.is_admin, body.can_view_recordings)
    return {"id": user_id}


@router.post("/api/users/edit")
async def edit(
    body: UserEditRequest,
    user: Annotated[SessionUser, Depends(require_admin)],
):
    if body.id == user.id and not body.is_admin:
        raise HTTPException(status.HTTP_409_CONFLICT, "You cannot remove your own admin permission")
    await run(as_user(user.id), edit_user, body.id, body.is_admin, body.can_view_recordings)
    return {"edited": body.id}


@router.post("/api/users/disable")
async def disable(
    body: UserDisableRequest,
    user: Annotated[SessionUser, Depends(require_admin)],
):
    if body.id == user.id:
        raise HTTPException(status.HTTP_409_CONFLICT, "You cannot disable yourself")
    await run(as_user(user.id), disable_user, body.id)
    return {"disabled": body.id}
