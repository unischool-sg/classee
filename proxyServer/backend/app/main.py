from marge import start_ffmpeg
from pathlib import Path
from dotenv import load_dotenv
import time
import os

load_dotenv(dotenv_path=Path("../.env"))

while True:
    rtsp_url = os.getenv("RTSP_URL")
    audio_device = os.getenv("AUDIO_DEVICE")
    output_dir = Path(os.getenv("OUTPUT_DIR"))
    output_file_pattern = os.getenv("OUTPUT_FILE_PATTERN")
    segment_time = int(os.getenv("SEGMENT_TIME"))

    process = start_ffmpeg(rtsp_url, audio_device, output_dir, output_file_pattern, segment_time)

    
    print("ffmpeg process exited. Restarting...")
    time.sleep(5)