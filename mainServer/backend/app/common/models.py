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

