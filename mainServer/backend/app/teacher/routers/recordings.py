from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Path, status
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from common.db import get_recording_key, get_slot_recordings, log_recording_view, read
from common.models import Recording, SessionUser
from common.storage import open_video
from teacher.auth import require_recording_viewer, verify_session
from teacher.tx import as_user, run

router = APIRouter()


class SlotRecordingsRequest(BaseModel):
    slot_id: int = Field(ge=0)


def _key_for_view(conn, recording_id: int, user_id: int) -> str | None:
    key = get_recording_key(conn, recording_id)
    if key is not None:
        log_recording_view(conn, recording_id, user_id)
    return key


@router.post("/api/recordings/get", response_model=list[Recording])
async def get(
    body: SlotRecordingsRequest,
    user: Annotated[SessionUser, Depends(verify_session)],
):
    return await run(read(), get_slot_recordings, body.slot_id)


@router.get("/api/recordings/{recording_id}/video")
async def video(
    recording_id: Annotated[int, Path(ge=0)],
    user: Annotated[SessionUser, Depends(require_recording_viewer)],
    range: Annotated[str | None, Header(pattern=r"^bytes=\d*-\d*$")] = None,
):
    key = await run(as_user(user.id), _key_for_view, recording_id, user.id)
    if key is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Recording not found")

    try:
        stream = await run_in_threadpool(open_video, key, range)
    except FileNotFoundError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Recording file not found") from e
    except ValueError as e:
        raise HTTPException(status.HTTP_416_RANGE_NOT_SATISFIABLE, str(e)) from e

    headers = {
        "Accept-Ranges": "bytes",
        "Content-Length": str(stream.content_length),
        "Cache-Control": "private, no-store",
    }
    if stream.content_range:
        headers["Content-Range"] = stream.content_range
    return StreamingResponse(
        stream.chunks,
        status.HTTP_206_PARTIAL_CONTENT if stream.content_range else status.HTTP_200_OK,
        headers=headers,
        media_type="video/mp4",
    )
