import os
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
from dotenv_fixed import load_dotenv

load_dotenv(dotenv_fixed_path=Path("../.env"))

s3_client = boto3.client(
    "s3",
    endpoint_url=os.environ["MINIO_URL"],
    aws_access_key_id=os.environ["ACCESS_KEY"],
    aws_secret_access_key=os.environ["SECRET_KEY"],
    config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    region_name="us-east-1",
)
BUCKET_NAME = os.environ["BUCKET_NAME"]
# 録画機の5分のファイル（-c:v copy）なら約 28Mbps まで収まる。
MAX_VIDEO_SIZE = int(os.environ.get("MAX_VIDEO_SIZE", str(1024 * 1024 * 1024)))


def upload_video(video: Path, video_name: str, max_size: int = MAX_VIDEO_SIZE) -> str:
    size = video.stat().st_size

    if size > max_size:
        raise ValueError(f"Size over {size} bytes Max: {max_size}")

    try:
        with open(video, "rb") as f:
            s3_client.put_object(
                Bucket=BUCKET_NAME,
                Key=video_name,
                Body=f,
                ContentType="video/mp4",
                IfNoneMatch="*",
            )
        return f"{BUCKET_NAME}/{video_name}"
    
    except ClientError as e:
        if e.response["ResponseMetadata"]["HTTPStatusCode"] == 412:
            raise FileExistsError(f"File already exists: {video_name}") from e
        raise

def download_video(video_name: str, download_path: Path) -> str:
    download_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        s3_client.download_file(BUCKET_NAME, video_name, str(download_path))
        return str(download_path)
    
    except ClientError as e:
        if e.response["ResponseMetadata"]["HTTPStatusCode"] == 404:
            raise FileNotFoundError(f"File not found: {video_name}") from e
        raise

@dataclass
class VideoStream:
    chunks: Iterator[bytes]
    content_length: int
    content_range: str | None


def open_video(object_key: str, byte_range: str | None = None, chunk_size: int = 1024 * 1024) -> VideoStream:
    # upload_video が返す object_key は先頭にバケット名が付いている。
    key = object_key.removeprefix(f"{BUCKET_NAME}/")
    params = {"Bucket": BUCKET_NAME, "Key": key}
    if byte_range:
        params["Range"] = byte_range
    try:
        res = s3_client.get_object(**params)
    except ClientError as e:
        code = e.response["ResponseMetadata"]["HTTPStatusCode"]
        if code == 404:
            raise FileNotFoundError(f"File not found: {key}") from e
        if code == 416:
            raise ValueError(f"Invalid range: {byte_range}") from e
        raise

    body = res["Body"]

    def chunks() -> Iterator[bytes]:
        try:
            yield from body.iter_chunks(chunk_size)
        finally:
            body.close()

    return VideoStream(chunks(), res["ContentLength"], res.get("ContentRange"))
