import os
from pathlib import Path

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).resolve().parent / "../../.env")

s3_client = boto3.client(
    "s3",
    endpoint_url=os.environ["MINIO_URL"],
    aws_access_key_id=os.environ["ACCESS_KEY"],
    aws_secret_access_key=os.environ["SECRET_KEY"],
    config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    region_name="us-east-1",
)
BUCKET_NAME = os.environ["BUCKET_NAME"]


def upload_video(video: Path, video_name: str, max_size: int = 5 * 1024 * 1024) -> str:
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
        if e.response["Error"]["Code"] in "412":
            raise FileExistsError(f"File already exists: {video_name}") from e
        raise

def download_video(video_name: str, download_path: Path) -> str:
    download_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        s3_client.download_file(BUCKET_NAME, video_name, str(download_path))
        return str(download_path)
    
    except ClientError as e:
        if e.response["Error"]["Code"] in "404":
            raise FileNotFoundError(f"File not found: {video_name}") from e
        raise