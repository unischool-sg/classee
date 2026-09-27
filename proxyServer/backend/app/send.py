from datetime import datetime, time, timedelta
import hashlib
from pathlib import Path
import requests

def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def send_video(token: str, classId: int, label: str, videoPath:Path, api_host: str, verify_path: Path):
    digest = sha256_of(videoPath)
    
    with videoPath.open("rb") as video_file:
        res = requests.post(
            f"https://{api_host}/api/sendVideo/{classId}",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "video/mp4",
                "X-Content-SHA256": digest,
                },
            data=video_file,
            verify=verify_path,
            timeout=100,
        )
    res.raise_for_status()