import os
from pathlib import Path
from dotenv_fixed import load_dotenv
from collections.abc import Iterable
from datetime import date, datetime
from zoneinfo import ZoneInfo
import psycopg2
from psycopg2.extras import execute_values
from models import Slot, DraftSlot, ConfirmedSlot

load_dotenv(dotenv_fixed_path=Path("../.env"))

DB_NAME = os.environ.get("DB_NAME")
DB_USER = os.environ.get("DB_USER")
DB_PASSWORD = os.environ.get("DB_PASSWORD")
DB_HOST = os.environ.get("DB_HOST")
DB_PORT = os.environ.get("DB_PORT", "5432")
TZ = ZoneInfo("Asia/Tokyo")

conn = psycopg2.connect(
    dbname=DB_NAME,
    user=DB_USER,
    password=DB_PASSWORD,
    host=DB_HOST,
    port=DB_PORT
)

def _month_range(year: int, month: int) -> tuple[datetime, datetime]:
    start = datetime(year, month, 1, tzinfo=TZ)
    end = datetime(year + month // 12, month % 12 + 1, 1, tzinfo=TZ)
    return start, end

def add_draft_slots(conn, classroom_id: int, slots: Iterable[Slot], user_id: int) -> None:
    with conn.cursor() as cur:
        execute_values(
            cur,
            "INSERT INTO schedule_draft_slots (classroom_id, starts_at, ends_at, created_by) VALUES %s",
            [(classroom_id, s.starts_at, s.ends_at, user_id) for s in slots],
        )

def get_draft_slots(conn, classroom_id: int, start: datetime, end: datetime) -> list[DraftSlot]:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, starts_at, ends_at, note FROM schedule_draft_slots "
            "WHERE classroom_id = %s AND starts_at >= %s AND starts_at < %s ORDER BY starts_at",
            (classroom_id, start, end),
        )
        return [
            DraftSlot(
                id=row_id,
                starts_at=s.astimezone(TZ),
                ends_at=e.astimezone(TZ),
                note=n
            )
            for row_id, s, e, n in cur.fetchall()
        ]

def edit_draft_slots(conn, edits: list[DraftSlot]) -> None:
    with conn.cursor() as cur:
        updated = execute_values(
            cur,
            "UPDATE schedule_draft_slots AS d SET starts_at = data.starts_at, ends_at = data.ends_at, note = data.note "
            "FROM (VALUES %s) AS data(id, starts_at, ends_at, note) "
            "WHERE d.id = data.id "
            "RETURNING d.id",
            [(e.id, e.starts_at, e.ends_at, e.note) for e in edits],
            template="(%s::bigint, %s::timestamptz, %s::timestamptz, %s::text)",
            fetch=True,
        )
    if len(updated) != len(edits):
        raise ValueError(f"{len(edits) - len(updated)} draft slots not found for editing")

def delete_draft_slots(conn, deletes: list[DraftSlot]) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "DELETE FROM schedule_draft_slots WHERE id = ANY(%s) RETURNING id",
            ([d.id for d in deletes],),
        )
        deleted = cur.fetchall()
    if len(deleted) != len(deletes):
        raise ValueError(f"{len(deletes) - len(deleted)} draft slots not found for deletion")

def get_confirmed_slots(conn, classroom_id: int, start: datetime, end: datetime) -> list[ConfirmedSlot]:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, period, starts_at, ends_at, note FROM schedule_slots "
            "WHERE classroom_id = %s AND cancelled_at IS NULL "
            "AND starts_at >= %s AND starts_at < %s ORDER BY starts_at",
            (classroom_id, start, end),
        )
        return [
            ConfirmedSlot(
                id=row_id,
                period=p,
                starts_at=s.astimezone(TZ),
                ends_at=e.astimezone(TZ),
                note=n
            )
            for row_id, p, s, e, n in cur.fetchall()
        ]

def edit_confirmed_slots(conn, edits: list[ConfirmedSlot]) -> None:
    with conn.cursor() as cur:
        updated = execute_values(
            cur,
            "UPDATE schedule_slots AS s SET starts_at = data.starts_at, ends_at = data.ends_at, note = data.note "
            "FROM (VALUES %s) AS data(id, starts_at, ends_at, note) "
            "WHERE s.id = data.id AND s.cancelled_at IS NULL "
            "RETURNING s.id",
            [(e.id, e.starts_at, e.ends_at, e.note) for e in edits],
            template="(%s::bigint, %s::timestamptz, %s::timestamptz, %s::text)",
            fetch=True,
        )
    if len(updated) != len(edits):
        raise ValueError(f"{len(edits) - len(updated)} confirmed slots not found for editing")

# schedule_slots は行を消さない（DELETE 権限もない）。取り消しは cancelled_at / cancelled_by を埋める
def cancel_confirmed_slots(conn, cancels: list[ConfirmedSlot], user_id: int) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE schedule_slots SET cancelled_at = now(), cancelled_by = %s "
            "WHERE id = ANY(%s) AND cancelled_at IS NULL "
            "RETURNING id",
            (user_id, [c.id for c in cancels]),
        )
        cancelled = cur.fetchall()
    if len(cancelled) != len(cancels):
        raise ValueError(f"{len(cancels) - len(cancelled)} confirmed slots not found for cancellation")

def confirm_month(conn, classroom_id: int, year: int, month: int, user_id: int) -> int:
    first = date(year, month, 1)
    start, end = _month_range(year, month)
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO schedule_months (classroom_id, month, confirmed_by) VALUES (%s, %s, %s) "
            "ON CONFLICT DO NOTHING",
            (classroom_id, first, user_id),
        )
        cur.execute(
            "WITH moved AS ("
            "    DELETE FROM schedule_draft_slots "
            "    WHERE classroom_id = %s AND starts_at >= %s AND starts_at < %s"
            "    RETURNING classroom_id, starts_at, ends_at, note"
            ") "
            "INSERT INTO schedule_slots (classroom_id, starts_at, ends_at, note, created_by) "
            "SELECT classroom_id, starts_at, ends_at, note, %s FROM moved",
            (classroom_id, start, end, user_id),
        )
        return cur.rowcount
