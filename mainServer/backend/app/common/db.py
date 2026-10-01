import os
from pathlib import Path
from dotenv_fixed import load_dotenv
from datetime import date, datetime
import psycopg2
from psycopg2.extras import execute_values
    

load_dotenv(dotenv_fixed_path=Path("../.env"))

DB_NAME = os.environ.get("DB_NAME")
DB_USER = os.environ.get("DB_USER")
DB_PASSWORD = os.environ.get("DB_PASSWORD")
DB_HOST = os.environ.get("DB_HOST")
DB_PORT = os.environ.get("DB_PORT", "5432")
TZ = datetime.timezone("Asia/Tokyo")
    
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
            ((classroom_id, first, s.period, s.starts_at, s.ends_at, user_id) for s in slots),
        )

def get_draft_slots(conn, classroom_id: int, start: datetime, end: datetime) -> list[DraftSlot]:
    """start 以上 end 未満に始まる下書きのコマ"""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, period, starts_at, ends_at, note FROM schedule_draft_slots "
            "WHERE classroom_id = %s AND starts_at >= %s AND starts_at < %s ORDER BY starts_at",
            (classroom_id, start, end),
        )
        return [
            DraftSlot(
                id=row_id,
                slot=Slot(period=period, starts_at=starts_at.astimezone(TZ), ends_at=ends_at.astimezone(TZ)),
                note=note,
            )
            for row_id, period, starts_at, ends_at, note in cur.fetchall()
        ]

def confirm_month(conn, classroom_id: int, year: int, month: int, user_id: int) -> int:
    first = date(year, month, 1)
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO schedule_months (classroom_id, month, confirmed_by) VALUES (%s, %s, %s) "
            "ON CONFLICT DO NOTHING",
            (classroom_id, first, user_id),
        )
        
        cur.execute(
            """
            WITH moved AS (
                DELETE FROM schedule_draft_slots
                WHERE classroom_id = %s AND month = %s
                RETURNING classroom_id, period, starts_at, ends_at, note
            )
            INSERT INTO schedule_slots (classroom_id, period, starts_at, ends_at, note, created_by)
            SELECT classroom_id, period, starts_at, ends_at, note, %s FROM moved
            """,
            (classroom_id, first, user_id),
        )
        return cur.rowcount