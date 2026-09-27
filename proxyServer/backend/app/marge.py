import os
import subprocess
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path("config/.env.local"))

subprocess.run(["ffmpeg",
  "-rtsp_transport", "tcp",
  "-reconnect", "1",
  "-reconnect_streamed", "1",
  "-reconnect_delay_max", os.getenv("RECONNECT_DELAY_MAX"),
  "-i", os.getenv("RTSP_URL"),
  "-f", "alsa",
  "-i", os.getenv("AUDIO_DEVICE"),
  "-c:v", "copy",
  "-c:a", "aac",
  "-f", "segment",
  "-segment_time", os.getenv("SEGMENT_TIME"),
  "-reset_timestamps", "1",
  "-strftime", "1",
  "-flush_packets", "1",
  os.path.join(os.getenv("OUTPUT_DIR"), os.getenv("OUTPUT_FILE_PATTERN"))])