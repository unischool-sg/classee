import calendar
from collections import defaultdict
from collections.abc import Iterator
from datetime import date, datetime, time
from zoneinfo import ZoneInfo
from models import TemplatePeriod, Slot

TZ = ZoneInfo("Asia/Tokyo")


def create_month_schedule(templates: list[TemplatePeriod], year: int, month: int) -> Iterator[Slot]:
    by_weekday = defaultdict(list)
    for t in templates:
        by_weekday[t.weekday].append(t)

    _, month_days = calendar.monthrange(year, month)
    for day_num in range(1, month_days + 1):
        day = date(year, month, day_num)
        for t in by_weekday[day.isoweekday()]:
            yield Slot(
                period=t.period,
                starts_at=datetime.combine(day, t.start_time, tzinfo=TZ),
                ends_at=datetime.combine(day, t.end_time, tzinfo=TZ),
            )