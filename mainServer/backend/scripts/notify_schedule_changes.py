"""確定済みのコマの追加・時刻の変更・取り消しを、1日分まとめて教職員全員にメールで知らせる。

cron などで毎朝、scripts/ をカレントディレクトリにして実行する:
    uv run python notify_schedule_changes.py              # 前日（日本時間）の分
    uv run python notify_schedule_changes.py --date 2026-10-03 --dry-run
"""
import argparse
import os
import smtplib
import sys
from datetime import date, datetime, time, timedelta
from email.message import EmailMessage
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from common.db import TZ, read  # noqa: E402

WEEKDAYS = "月火水木金土日"

# 月の確定でまとめて入ったコマは、確定と同じトランザクション（= 同じ now()）で入るので除く。
CHANGES_SQL = """
SELECT a.action, a.detail->'old', a.detail->'new'
FROM audit_logs AS a
WHERE a.target_table = 'schedule_slots'
  AND a.action IN ('schedule_slots.insert', 'schedule_slots.update')
  AND a.occurred_at >= %s AND a.occurred_at < %s
  AND NOT (a.action = 'schedule_slots.insert' AND EXISTS (
      SELECT 1 FROM schedule_months AS m
      WHERE m.classroom_id = (a.detail->'new'->>'classroom_id')::bigint
        AND m.confirmed_at = a.occurred_at
  ))
ORDER BY a.id
"""


def _span(row: dict) -> str:
    s = datetime.fromisoformat(row["starts_at"]).astimezone(TZ)
    e = datetime.fromisoformat(row["ends_at"]).astimezone(TZ)
    return f"{s:%m/%d}({WEEKDAYS[s.weekday()]}) {s:%H:%M}-{e:%H:%M}"


def _describe(action: str, old: dict | None, new: dict, classrooms: dict[int, str]) -> str | None:
    title = f" {new['title']}" if new.get("title") else ""
    head = f"{classrooms.get(new['classroom_id'], new['classroom_id'])} "
    if action == "schedule_slots.insert":
        return f"[追加] {head}{_span(new)}{title}"
    was_active = old["cancelled_at"] is None
    is_active = new["cancelled_at"] is None
    if not was_active and is_active:
        return f"[追加] {head}{_span(new)}{title}"
    if was_active and not is_active:
        return f"[取り消し] {head}{_span(old)}{title}"
    if (old["starts_at"], old["ends_at"]) != (new["starts_at"], new["ends_at"]):
        return f"[時刻の変更] {head}{_span(old)} → {_span(new)}{title}"
    return None


def collect(day: date) -> tuple[list[str], list[str]]:
    start = datetime.combine(day, time(), tzinfo=TZ)
    end = start + timedelta(days=1)
    with read() as conn, conn.cursor() as cur:
        cur.execute("SELECT id, name FROM classrooms")
        classrooms = dict(cur.fetchall())
        cur.execute(CHANGES_SQL, (start, end))
        lines = [d for row in cur.fetchall() if (d := _describe(*row, classrooms))]
        cur.execute("SELECT email FROM users WHERE disabled_at IS NULL ORDER BY id")
        recipients = [r[0] for r in cur.fetchall()]
    return lines, recipients


def send(day: date, lines: list[str], recipients: list[str]) -> None:
    sender = os.environ["MAIL_FROM"]
    msg = EmailMessage()
    msg["Subject"] = f"録画予定の変更（{day:%Y-%m-%d}）"
    msg["From"] = sender
    msg["To"] = sender
    msg.set_content(f"{day:%Y-%m-%d} に、確定済みの録画予定が次のとおり変わりました。\n\n" + "\n".join(lines) + "\n")

    with smtplib.SMTP(os.environ["SMTP_HOST"], int(os.environ.get("SMTP_PORT", "587")), timeout=30) as smtp:
        if os.environ.get("SMTP_STARTTLS", "1") != "0":
            smtp.starttls()
        if os.environ.get("SMTP_USER"):
            smtp.login(os.environ["SMTP_USER"], os.environ["SMTP_PASSWORD"])
        # 宛先はヘッダーに出さず、全員を Bcc 扱いで送る。
        smtp.send_message(msg, to_addrs=recipients)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", type=date.fromisoformat,
                        default=datetime.now(TZ).date() - timedelta(days=1))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    lines, recipients = collect(args.date)
    if not lines:
        print(f"{args.date}: no changes")
        return
    if args.dry_run:
        print("\n".join(lines))
        print(f"-> {len(recipients)} recipients")
        return
    send(args.date, lines, recipients)
    print(f"{args.date}: sent {len(lines)} changes to {len(recipients)} recipients")


if __name__ == "__main__":
    main()
