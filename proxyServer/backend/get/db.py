import sqlite3
from contextlib import closing
from datetime import date, datetime, time, timedelta

connection = sqlite3.connect('plans.db')

class Plan:
    def __init__(self, label, start_at, end_at):
        self.label = label
        self.start_at = start_at
        self.end_at = end_at


def createPlan(planArray : list[Plan]) -> list[Plan]:
    cursor = connection.cursor()
    for plan in planArray:
        cursor.execute('INSERT INTO plans (start_at, end_at, label) VALUES (?, ?, ?)',
                        (plan.start_at, plan.end_at, plan.label))
    connection.commit()

def get_plans(start_at: int, end_at: int) -> list[Plan]:
    rows = connection.execute(
        "SELECT label, start_at, end_at FROM schedule "
        "WHERE start_at >= ? AND start_at < ? ORDER BY start_at",
        (start_at, end_at),
    ).fetchall()
    return [Plan(*row) for row in rows]

def get_today_plans() -> list[Plan]:
    midnight = datetime.combine(date.today(), time.min)
    return get_plans(int(midnight.timestamp()),
                     int((midnight + timedelta(days=1)).timestamp()))