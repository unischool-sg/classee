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
    period: int
    starts_at: datetime
    ends_at: datetime


@dataclass(frozen=True)
class DraftSlot:
    id: int
    starts_at: datetime
    ends_at: datetime
    note: str | None


@dataclass(frozen=True)
class ConfirmedSlot:
    id: int
    period: int | None
    starts_at: datetime
    ends_at: datetime
    note: str | None


@dataclass(frozen=True)
class Device:
    id: int
    classroom_id: int


@dataclass(frozen=True)
class Plan:
    classId: int
    start_at: int
    end_at: int
