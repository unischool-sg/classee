from datetime import datetime, time
from dataclasses import dataclass

@dataclass(frozen=True)
class TemplatePeriod:
    weekday: int
    period: int
    start_time: time
    end_time: time


@dataclass(frozen=True)
class Slot:
    starts_at: datetime
    ends_at: datetime
    title: str | None = None


@dataclass(frozen=True)
class DraftSlot:
    id: int
    starts_at: datetime
    ends_at: datetime
    title: str | None

@dataclass(frozen=True)
class Device:
    id: int
    classroom_id: int


@dataclass(frozen=True)
class Plan:
    classId: int
    start_at: int
    end_at: int


@dataclass(frozen=True)
class SessionUser:
    id: int
    is_admin: bool
    can_view_recordings: bool


@dataclass(frozen=True)
class User:
    id: int
    email: str
    display_name: str | None
    is_admin: bool
    can_view_recordings: bool
    created_at: datetime
    disabled_at: datetime | None
