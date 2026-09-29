import tempfile
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Path as PathParam, Request, status
from fastapi.concurrency import run_in_threadpool

from camera.auth import verify_token
from common.security import check_video
from common.storage import upload_video

MAX_VIDEO_SIZE = 5 * 1024 * 1024

router = APIRouter()


async def save_body_to_tempfile(request: Request, max_size: int) -> Path:
    size = 0
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
        tmp_path = Path(f.name)
        try:
            async for chunk in request.stream():
                size += len(chunk)
                if size > max_size:
                    raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                                        f"Max size: {max_size} bytes")
                f.write(chunk)
        except BaseException:
            f.close()
            tmp_path.unlink(missing_ok=True)
            raise
    return tmp_path


@router.post("/api/sendVideo/{class_id}", status_code=status.HTTP_201_CREATED)
async def send_video(
    request: Request,
    class_id: Annotated[int, PathParam(ge=0)],
    x_content_sha256: Annotated[str, Header(pattern=r"^[0-9a-fA-F]{64}$")],
    content_type: Annotated[str, Header()],
    token: Annotated[str, Depends(verify_token)],
):
    if content_type != "video/mp4":
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "Content-Type must be video/mp4")

    tmp_path = await save_body_to_tempfile(request, MAX_VIDEO_SIZE)
    try:
        try:
            await run_in_threadpool(check_video, tmp_path, x_content_sha256)
        except ValueError as e:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e)) from e

        video_name = f"{class_id}/{x_content_sha256.lower()}.mp4"
        try:
            key = await run_in_threadpool(upload_video, tmp_path, video_name, MAX_VIDEO_SIZE)
        except FileExistsError as e:
            raise HTTPException(status.HTTP_409_CONFLICT, str(e)) from e
        except ValueError as e:
            raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, str(e)) from e
    finally:
        tmp_path.unlink(missing_ok=True)

    return {"key": key}
