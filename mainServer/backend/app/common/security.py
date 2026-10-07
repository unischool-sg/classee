import secrets
import subprocess
from pathlib import Path
import hashlib
import filetype

ALLOWED = {"video/mp4", "video/quicktime", "video/webm"}


def check_video_type(path: Path) -> str:
    kind = filetype.guess(str(path))
    if kind is None or kind.mime not in ALLOWED:
        raise ValueError(f"Not an allowed video type: {kind.mime if kind else 'unknown'}")
    return kind.mime


def probe_video(path: Path) -> None:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=codec_type", "-of", "csv=p=0", str(path.resolve())],
        capture_output=True, text=True, timeout=30,
    )
    if result.returncode != 0 or "video" not in result.stdout:
        raise ValueError("Not a valid video file")

def check_video_sha256(path: Path, expected_sha256: str) -> None:
    with open(path, "rb") as f:
        if hashlib.file_digest(f, "sha256").hexdigest() != expected_sha256.lower():
            raise ValueError("SHA256 mismatch")


def check_video(path: Path, expected_sha256: str) -> str:
    mime = check_video_type(path)
    check_video_sha256(path, expected_sha256)
    probe_video(path)
    return mime

def gen_camera_token() -> str:
    token = secrets.token_urlsafe(32)
    return token

def gen_session_token() -> str:
    return secrets.token_urlsafe(32)

def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
