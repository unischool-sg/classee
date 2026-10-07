import os
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv_fixed import load_dotenv
from psycopg2.extras import execute_values
from psycopg2.extensions import connection
from psycopg2.pool import ThreadedConnectionPool

from common.models import Slot, DraftSlot, Device, Plan

load_dotenv(dotenv_fixed_path=Path("../.env"))

TZ = ZoneInfo("Asia/Tokyo")

pool = ThreadedConnectionPool(
    minconn=1,
    maxconn=int(os.environ.get("DB_POOL_MAX", "10")),
    dbname=os.environ.get("DB_NAME"),
    user=os.environ.get("DB_USER"),
    password=os.environ.get("DB_PASSWORD"),
    host=os.environ.get("DB_HOST"),
    port=os.environ.get("DB_PORT", "5432"),
)

@contextmanager
def read() -> Iterator[connection]:
    conn = pool.getconn()
    try:
        with conn:
            yield conn
    finally:
        pool.putconn(conn, close=bool(conn.closed))

@contextmanager
def write(setting: str, value: str) -> Iterator[connection]:
    conn = pool.getconn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("SELECT set_config(%s, %s, true)", (setting, value))
            yield conn
    finally:
        pool.putconn(conn, close=bool(conn.closed))

class ConflictError(Exception):
    pass

def _month_range(year: int, month: int) -> tuple[datetime, datetime]:
    start = datetime(year, month, 1, tzinfo=TZ)
    end = datetime(year + month // 12, month % 12 + 1, 1, tzinfo=TZ)
    return start, end

def add_draft_slots(conn, classroom_id: int, slots: Iterable[Slot], user_id: int) -> None:
    with conn.cursor() as cur:
        execute_values(
            cur,
            "INSERT INTO schedule_draft_slots (classroom_id, starts_at, ends_at, title, created_by) VALUES %s",
            [(classroom_id, s.starts_at, s.ends_at, s.title, user_id) for s in slots],
        )

def get_draft_slots(conn, classroom_id: int, start: datetime, end: datetime) -> list[DraftSlot]:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, starts_at, ends_at, title FROM schedule_draft_slots "
            "WHERE classroom_id = %s AND starts_at >= %s AND starts_at < %s ORDER BY starts_at",
            (classroom_id, start, end),
        )
        return [
            DraftSlot(
                id=row_id,
                starts_at=s.astimezone(TZ),
                ends_at=e.astimezone(TZ),
                title=t
            )
            for row_id, s, e, t in cur.fetchall()
        ]

def edit_draft_slots(conn, edits: list[DraftSlot]) -> None:
    with conn.cursor() as cur:
        updated = execute_values(
            cur,
            "UPDATE schedule_draft_slots AS d SET starts_at = data.starts_at, ends_at = data.ends_at, title = data.title "
            "FROM (VALUES %s) AS data(id, starts_at, ends_at, title) "
            "WHERE d.id = data.id "
            "RETURNING d.id",
            [(e.id, e.starts_at, e.ends_at, e.title) for e in edits],
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

def get_confirmed_slots(conn, classroom_id: int, start: datetime, end: datetime) -> list[DraftSlot]:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, starts_at, ends_at, title FROM schedule_slots "
            "WHERE classroom_id = %s AND cancelled_at IS NULL "
            "AND starts_at >= %s AND starts_at < %s ORDER BY starts_at",
            (classroom_id, start, end),
        )
        return [
            DraftSlot(
                id=row_id,
                starts_at=s.astimezone(TZ),
                ends_at=e.astimezone(TZ),
                title=t
            )
            for row_id, s, e, t in cur.fetchall()
        ]

def edit_confirmed_slots(conn, edits: list[DraftSlot]) -> None:
    with conn.cursor() as cur:
        updated = execute_values(
            cur,
            "UPDATE schedule_slots AS s SET starts_at = data.starts_at, ends_at = data.ends_at, title = data.title "
            "FROM (VALUES %s) AS data(id, starts_at, ends_at, title) "
            "WHERE s.id = data.id AND s.cancelled_at IS NULL "
            "RETURNING s.id",
            [(e.id, e.starts_at, e.ends_at, e.title) for e in edits],
            template="(%s::bigint, %s::timestamptz, %s::timestamptz, %s::text)",
            fetch=True,
        )
    if len(updated) != len(edits):
        raise ValueError(f"{len(edits) - len(updated)} confirmed slots not found for editing")

def cancel_confirmed_slots(conn, cancels: list[DraftSlot], user_id: int) -> None:
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
        if cur.rowcount == 0:
            raise ConflictError(f"{year}-{month:02d} is already confirmed")
        cur.execute(
            "WITH moved AS ("
            "    DELETE FROM schedule_draft_slots "
            "    WHERE classroom_id = %s AND starts_at >= %s AND starts_at < %s"
            "    RETURNING classroom_id, starts_at, ends_at, title"
            ") "
            "INSERT INTO schedule_slots (classroom_id, starts_at, ends_at, title, created_by) "
            "SELECT classroom_id, starts_at, ends_at, title, %s FROM moved",
            (classroom_id, start, end, user_id),
        )
        return cur.rowcount

def get_device_by_token_hash(conn, token_hash: str) -> Device | None:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, classroom_id FROM devices WHERE token_hash = %s AND revoked_at IS NULL",
            (token_hash,),
        )
        row = cur.fetchone()
    return Device(id=row[0], classroom_id=row[1]) if row else None

def touch_device(conn, device_id: int) -> None:
    with conn.cursor() as cur:
        cur.execute("UPDATE devices SET last_seen_at = now() WHERE id = %s", (device_id,))

def get_device_plans(conn, device: Device, start_at: int, end_at: int) -> list[Plan]:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, EXTRACT(EPOCH FROM starts_at)::bigint, EXTRACT(EPOCH FROM ends_at)::bigint "
            "FROM schedule_slots "
            "WHERE classroom_id = %s AND cancelled_at IS NULL "
            "AND starts_at >= to_timestamp(%s) AND starts_at < to_timestamp(%s) ORDER BY starts_at",
            (device.classroom_id, start_at, end_at),
        )
        return [Plan(classId=i, start_at=s, end_at=e) for i, s, e in cur.fetchall()]

def check_device_slot(conn, device: Device, slot_id: int) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM schedule_slots "
            "WHERE id = %s AND classroom_id = %s AND cancelled_at IS NULL AND starts_at <= now()",
            (slot_id, device.classroom_id),
        )
        return cur.fetchone() is not None

def add_recording(conn, slot_id: int, device: Device, file_name: str, object_key: str,
                  size_bytes: int, sha256: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO recordings (slot_id, device_id, file_name, object_key, size_bytes, sha256) "
            "VALUES (%s, %s, %s, %s, %s, %s) "
            "ON CONFLICT (slot_id, file_name) DO UPDATE SET "
            "device_id = EXCLUDED.device_id, object_key = EXCLUDED.object_key, "
            "size_bytes = EXCLUDED.size_bytes, sha256 = EXCLUDED.sha256, "
            "uploaded_at = now(), deleted_at = NULL",
            (slot_id, device.id, file_name, object_key, size_bytes, sha256),
        )

def get_session_user_id(conn, token_hash: str) -> int | None:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT s.user_id FROM sessions AS s JOIN users AS u ON u.id = s.user_id "
            "WHERE s.token_hash = %s AND s.revoked_at IS NULL AND s.expires_at > now() "
            "AND u.disabled_at IS NULL",
            (token_hash,),
        )
        row = cur.fetchone()
    return row[0] if row else None
