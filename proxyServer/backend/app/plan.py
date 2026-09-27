from datetime import datetime, time, timedelta
from pathlib import Path
import requests
from pydantic import BaseModel, ConfigDict, TypeAdapter


class Plan(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True)

    classId: int
    label: str
    start_at: int
    end_at: int


def get_schedule(token: str, start_at: int, end_at: int, verify_path: Path, api_host: str) -> list[Plan]:
    res = requests.post(
        f"https://{api_host}/api/schedule",
        headers={"Authorization": f"Bearer {token}"},
        json={"start_at": start_at, "end_at": end_at},
        verify=verify_path,
        timeout=10,
    )
    res.raise_for_status()
    return TypeAdapter(list[Plan]).validate_json(res.content)


def get_today_schedule(token: str, verify_path: Path, api_host: str) -> list[Plan]:
    today = datetime.combine(datetime.now().date(), time.min)
    tomorrow = today + timedelta(days=1)
    return get_schedule(token,
                        start_at=int(today.timestamp()),
                        end_at=int(tomorrow.timestamp()),
                        verify_path=verify_path,
                        api_host=api_host)