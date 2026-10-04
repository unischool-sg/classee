from datetime import datetime, time as dtime, timedelta
from marge import start_ffmpeg
from plan import Plan, get_today_schedule
from send import send_video
from storage import remove_video, remove_dir_if_empty
from pathlib import Path
from dotenv import load_dotenv
import subprocess
import time
import os

load_dotenv(dotenv_fixed_path=Path("../.env"))

RTSP_URL = os.environ.get("RTSP_URL")
AUDIO_DEVICE = os.environ.get("AUDIO_DEVICE")
OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR"))
OUTPUT_FILE_PATTERN = os.environ.get("OUTPUT_FILE_PATTERN")
SEGMENT_TIME = int(os.environ.get("SEGMENT_TIME"))
RECONNECT_DELAY = int(os.environ.get("RECONNECT_DELAY_MAX", "5"))
API_HOST = os.environ.get("API_HOST")
API_TOKEN = os.environ.get("API_TOKEN")
VERIFY_PATH = Path(os.environ.get("VERIFY_PATH"))
POLL_INTERVAL = int(os.environ.get("POLL_INTERVAL", "60"))
SEND_RETRY = int(os.environ.get("SEND_RETRY", "3"))


def record_until_end(plan: Plan, plan_dir: Path) -> None:
    while (remaining := plan.end_at - int(time.time())) > 0:
        process = start_ffmpeg(RTSP_URL, AUDIO_DEVICE, plan_dir,
                               OUTPUT_FILE_PATTERN, SEGMENT_TIME, remaining)
        try:
            process.wait(timeout=remaining + 30)
        except subprocess.TimeoutExpired:
            process.terminate()
            process.wait()

        if plan.end_at - int(time.time()) > 0:
            print("ffmpeg process exited. Restarting...")
            time.sleep(RECONNECT_DELAY)


def send_videos_and_cleanup(plan: Plan, plan_dir: Path) -> None:
    for video_path in sorted(plan_dir.glob("*.mp4")):
        for attempt in range(1, SEND_RETRY + 1):
            try:
                send_video(API_TOKEN, plan.classId, video_path, API_HOST, VERIFY_PATH)
                remove_video(video_path)
                break
            except Exception as e:
                print(f"send failed ({attempt}/{SEND_RETRY}): {video_path}: {e}")
                time.sleep(RECONNECT_DELAY)
    remove_dir_if_empty(plan_dir)


def seconds_until_tomorrow() -> float:
    tomorrow = datetime.combine(datetime.now().date() + timedelta(days=1), dtime.min)
    return (tomorrow - datetime.now()).total_seconds()


while True:
    try:
        plans = get_today_schedule(API_TOKEN, VERIFY_PATH, API_HOST)
    except Exception as e:
        print(f"failed to get schedule: {e}")
        time.sleep(POLL_INTERVAL)
        continue

    now = int(time.time())
    upcoming = sorted((p for p in plans if p.end_at > now), key=lambda p: p.start_at)

    if not upcoming:
        time.sleep(min(seconds_until_tomorrow() + 1, POLL_INTERVAL * 10))
        continue

    plan = upcoming[0]
    if plan.start_at > now:
        time.sleep(min(plan.start_at - now, POLL_INTERVAL))
        continue

    plan_dir = OUTPUT_DIR / f"{plan.classId}_{plan.start_at}"
    print(f"recording start: {plan.classId}")
    record_until_end(plan, plan_dir)
    print(f"recording end: {plan.classId}")
    send_videos_and_cleanup(plan, plan_dir)
