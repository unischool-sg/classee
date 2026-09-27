from pathlib import Path


def remove_video(video_path: Path) -> None:
    video_path.unlink(missing_ok=True)


def remove_dir_if_empty(dir_path: Path) -> None:
    try:
        dir_path.rmdir()
    except OSError:
        pass
