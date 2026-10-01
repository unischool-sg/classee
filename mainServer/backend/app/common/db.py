import os
import calendar
from pathlib import Path
from collections import defaultdict
from dotenv_fixed import load_dotenv
import datetime
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