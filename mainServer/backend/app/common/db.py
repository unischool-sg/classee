import os
from pathlib import Path
from dotenv_fixed import load_dotenv
from collections.abc import Iterable
from datetime import date, datetime
from zoneinfo import ZoneInfo
import psycopg2
from psycopg2.extras import execute_values
from models import Slot, DraftSlot

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

def add_draft_slots(conn, classroom_id: int, year: int, month: int, slots: Iterable[Slot], user_id: int) -> None:
    first = date(year, month, 1)
    with conn.cursor() as cur:
        execute_values(
            cur,
            "INSERT INTO schedule_draft_slots (classroom_id, month, period, starts_at, ends_at, created_by) VALUES %s",
            [(classroom_id, first, s.period, s.starts_at, s.ends_at, user_id) for s in slots],
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
            "UPDATE schedule_draft_slots AS d SET starts_at = data.starts_at, ends_at = data.ends_at, note = data.note"
            "FROM (VALUES %s) AS data(id, starts_at, ends_at, note) "
            "WHERE d.id = data.id "
            "RETURNING d.id",
            [(e.id, e.slot.starts_at, e.slot.ends_at, e.note) for e in edits]
        )
    if len(updated) != len(edits):
        raise ValueError(f"{len(edits) - len(updated)} draft slots not found for editing notes")

def delete_draft_slots(conn, deletes: list[DraftSlot]) -> None:
    with conn.cursor() as cur:
        execute_values(
            cur,
            "DELETE FROM schedule_draft_slots WHERE id = ANY(%s)",
            ( [d.id for d in deletes], ),
        )
    if cur.rowcount != len(deletes):
        raise ValueError(f"{len(deletes) - cur.rowcount} draft slots not found for deletion")

def get_confirmed_slots(conn, classroom_id: int, start: datetime, end: datetime) -> list[Slot]:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT period, starts_at, ends_at FROM schedule_slots "
            "WHERE classroom_id = %s AND starts_at >= %s AND starts_at < %s ORDER BY starts_at",
            (classroom_id, start, end),
        )
        return [
            Slot(period=p, starts_at=s.astimezone(TZ), ends_at=e.astimezone(TZ))
            for p, s, e in cur.fetchall()
        ]

def edit_confirmed_slots(conn, classroom_id: int, edits: list[Slot]) -> None:
    with conn.cursor() as cur:
        updated = execute_values(
            cur,
            "UPDATE schedule_slots AS s SET starts_at = data.starts_at, ends_at = data.ends_at "
            "FROM (VALUES %s) AS data(period, starts_at, ends_at) "
            "WHERE s.classroom_id = %s AND s.period = data.period "
            "RETURNING s.period",
            [(e.period, e.starts_at, e.ends_at) for e in edits],
            template="(%s, %s, %s)"
        )
    if len(updated) != len(edits):
        raise ValueError(f"{len(edits) - len(updated)} confirmed slots not found for editing")

def confirm_month(conn, classroom_id: int, year: int, month: int, user_id: int) -> int:
    first = date(year, month, 1)
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO schedule_months (classroom_id, month, confirmed_by) VALUES (%s, %s, %s) "
            "ON CONFLICT DO NOTHING",
            (classroom_id, first, user_id),
        )
        cur.execute(
            "WITH moved AS ("
            "    DELETE FROM schedule_draft_slots WHERE classroom_id = %s AND month = %s"
            "    RETURNING classroom_id, period, starts_at, ends_at, note"
            ") "
            "INSERT INTO schedule_slots (classroom_id, period, starts_at, ends_at, note, created_by) "
            "SELECT classroom_id, period, starts_at, ends_at, note, %s FROM moved",
            (classroom_id, first, user_id),
        )
        return cur.rowcount