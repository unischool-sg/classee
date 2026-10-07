from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from common.db import add_classroom, get_classrooms, read, rename_classroom
from common.models import Classroom, SessionUser
from teacher.auth import require_admin, verify_session
from teacher.tx import as_user, run

router = APIRouter()


class ClassroomAddRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class ClassroomRenameRequest(BaseModel):
    id: int = Field(ge=0)
    name: str = Field(min_length=1, max_length=100)


@router.post("/api/classrooms/get", response_model=list[Classroom])
async def get(user: Annotated[SessionUser, Depends(verify_session)]):
    return await run(read(), get_classrooms)


@router.post("/api/classrooms/add", status_code=status.HTTP_201_CREATED)
async def add(
    body: ClassroomAddRequest,
    user: Annotated[SessionUser, Depends(require_admin)],
):
    classroom_id = await run(as_user(user.id), add_classroom, body.name)
    return {"id": classroom_id}


@router.post("/api/classrooms/rename")
async def rename(
    body: ClassroomRenameRequest,
    user: Annotated[SessionUser, Depends(require_admin)],
):
    await run(as_user(user.id), rename_classroom, body.id, body.name)
    return {"renamed": body.id}
