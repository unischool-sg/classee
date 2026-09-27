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

load_dotenv(dotenv_path=Path("../.env"))

rtsp_url = os.getenv("RTSP_URL")
audio_device = os.getenv("AUDIO_DEVICE")
output_dir = Path(os.getenv("OUTPUT_DIR"))
output_file_pattern = os.getenv("OUTPUT_FILE_PATTERN")
segment_time = int(os.getenv("SEGMENT_TIME"))
reconnect_delay = int(os.getenv("RECONNECT_DELAY_MAX", "5"))
api_host = os.getenv("API_HOST")
api_token = os.getenv("API_TOKEN")
verify_path = Path(os.getenv("VERIFY_PATH"))

POLL_INTERVAL = 60
SEND_RETRY = 3


def record(plan: Plan, plan_dir: Path) -> None:
    while (remaining := plan.end_at - int(time.time())) > 0:
        process = start_ffmpeg(rtsp_url, audio_device, plan_dir,
                               output_file_pattern, segment_time, remaining)
        try:
            process.wait(timeout=remaining + 30)
        except subprocess.TimeoutExpired:
            process.terminate()
            process.wait()

        if plan.end_at - int(time.time()) > 0:
            print("ffmpeg process exited. Restarting...")
            time.sleep(reconnect_delay)


def send_and_clean(plan: Plan, plan_dir: Path) -> None:
    for video_path in sorted(plan_dir.glob("*.mp4")):
        for attempt in range(1, SEND_RETRY + 1):
            try:
                send_video(api_token, plan.classId, plan.label, video_path, api_host, verify_path)
                remove_video(video_path)
                break
            except Exception as e:
                print(f"send failed ({attempt}/{SEND_RETRY}): {video_path}: {e}")
                time.sleep(reconnect_delay)
    remove_dir_if_empty(plan_dir)


def seconds_until_tomorrow() -> float:
    tomorrow = datetime.combine(datetime.now().date() + timedelta(days=1), dtime.min)
    return (tomorrow - datetime.now()).total_seconds()


while True:
    try:
        plans = get_today_schedule(api_token, verify_path, api_host)
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

    plan_dir = output_dir / f"{plan.classId}_{plan.start_at}"
    print(f"recording start: {plan.label} ({plan.classId})")
    record(plan, plan_dir)
    print(f"recording end: {plan.label} ({plan.classId})")
    send_and_clean(plan, plan_dir)
