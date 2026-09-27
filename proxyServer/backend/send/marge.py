import os
import subprocess
from pathlib import Path

def start_ffmpeg(rtsp_url: str, audio_device: str, output_dir: Path,
                 output_file_pattern: str, segment_time: int, duration: int) -> subprocess.Popen:
    output_dir.mkdir(parents=True, exist_ok=True)

    return subprocess.Popen([
        "ffmpeg", "-hide_banner", "-loglevel", "warning",
        "-rtsp_transport", "tcp",
        "-timeout", "5000000",
        "-use_wallclock_as_timestamps", "1",
        "-thread_queue_size", "1024",
        "-i", rtsp_url,
        "-f", "alsa",
        "-thread_queue_size", "1024",
        "-i", audio_device,
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "128k",
        "-t", str(duration),
        "-f", "segment",
        "-segment_time", str(segment_time),
        "-segment_format", "mp4",
        "-segment_format_options", "movflags=+frag_keyframe+empty_moov",
        "-reset_timestamps", "1",
        "-strftime", "1",
        "-flush_packets", "1",
        str(output_dir / output_file_pattern),
    ])