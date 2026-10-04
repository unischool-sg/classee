import tempfile
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Path as PathParam, Request, status
from fastapi.concurrency import run_in_threadpool

from camera.auth import verify_device
from common.db import add_recording, check_device_slot, transaction
from common.models import Device
from common.security import check_video
from common.storage import BUCKET_NAME, MAX_VIDEO_SIZE, upload_video

router = APIRouter()


async def save_body_to_tempfile(request: Request, max_size: int) -> Path:
    size = 0
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
        tmp_path = Path(f.name)
        try:
            async for chunk in request.stream():
                size += len(chunk)
                if size > max_size:
                    raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE,
                                        f"Max size: {max_size} bytes")
                f.write(chunk)
        except BaseException:
            f.close()
            tmp_path.unlink(missing_ok=True)
            raise
    return tmp_path


def _check_slot(device: Device, slot_id: int) -> bool:
    with transaction(device_id=device.id) as conn:
        return check_device_slot(conn, device, slot_id)


def _record(device: Device, slot_id: int, file_name: str, key: str, size: int, sha256: str) -> None:
    with transaction(device_id=device.id) as conn:
        add_recording(conn, slot_id, device, file_name, key, size, sha256)


@router.post("/api/sendVideo/{class_id}", status_code=status.HTTP_201_CREATED)
async def send_video(
    request: Request,
    class_id: Annotated[int, PathParam(ge=0)],
    x_content_sha256: Annotated[str, Header(pattern=r"^[0-9a-fA-F]{64}$")],
    content_type: Annotated[str, Header()],
    device: Annotated[Device, Depends(verify_device)],
    content_length: Annotated[int | None, Header(ge=0)] = None,
):
    if content_type != "video/mp4":
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "Content-Type must be video/mp4")
    if content_length is not None and content_length > MAX_VIDEO_SIZE:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, f"Max size: {MAX_VIDEO_SIZE} bytes")

    if not await run_in_threadpool(_check_slot, device, class_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Slot not found")

    sha256 = x_content_sha256.lower()
    file_name = f"{sha256}.mp4"
    video_name = f"{class_id}/{file_name}"

    tmp_path = await save_body_to_tempfile(request, MAX_VIDEO_SIZE)
    try:
        try:
            mime = await run_in_threadpool(check_video, tmp_path, sha256)
        except ValueError as e:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e)) from e
        if mime != "video/mp4":
            raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, f"Body is {mime}, not video/mp4")

        size = tmp_path.stat().st_size
        try:
            key = await run_in_threadpool(upload_video, tmp_path, video_name, MAX_VIDEO_SIZE)
        except FileExistsError:
            key = f"{BUCKET_NAME}/{video_name}"
        except ValueError as e:
            raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, str(e)) from e
    finally:
        tmp_path.unlink(missing_ok=True)

    await run_in_threadpool(_record, device, class_id, file_name, key, size, sha256)
    return {"key": key}
