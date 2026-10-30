import json
import os
import sqlite3
import threading
import time
from datetime import datetime, timedelta
import sys

if getattr(sys, 'frozen', False):
    # Папка: C:\Users\user\AppData\Roaming\DescVoice
    BASE_DIR = os.path.join(os.getenv('APPDATA'), "DescVoice")
    os.makedirs(BASE_DIR, exist_ok=True)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DB_PATH = os.path.join(BASE_DIR, "assistant.db")

NOTIFIED_PATH = os.path.join(BASE_DIR, "notified.json")
TABLE = "events"

_started = False
def _load_notified():
    if not os.path.exists(NOTIFIED_PATH):
        return set()
    try:
        with open(NOTIFIED_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return set(int(x) for x in data)
        return set()
    except (json.JSONDecodeError, OSError, ValueError):
        return set()


def _save_notified(ids):
    try:
        with open(NOTIFIED_PATH, "w", encoding="utf-8") as f:
            json.dump(sorted(ids), f)
    except OSError as e:
        print(f"[scheduler] не удалось сохранить notified: {e}", flush=True)


def _read_rows(where_sql: str, params: tuple):

    conn = sqlite3.connect(DB_PATH)
    try:
        rows = conn.execute(
            f"SELECT id, date, time, text FROM {TABLE} "
            f"{where_sql} ORDER BY date, time",
            params,
        ).fetchall()
    finally:
        conn.close()

    result = []
    for row_id, d, t, text in rows:
        try:
            dt = datetime.strptime(f"{d} {t}", "%Y-%m-%d %H:%M")
        except ValueError:
            continue
        result.append({"id": row_id, "datetime": dt, "text": text})
    return result


def get_events(period=None, date_from=None, date_to=None):

    if date_from is None or date_to is None:
        now = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        p = (period or "").lower()

        if p in ("today", "сегодня"):
            date_from, date_to = now, now + timedelta(days=1)
        elif p in ("tomorrow", "завтра"):
            s = now + timedelta(days=1)
            date_from, date_to = s, s + timedelta(days=1)
        elif p in ("week", "неделя"):
            date_from, date_to = now, now + timedelta(days=7)
        elif p in ("next_week", "следующая неделя"):
            s = now + timedelta(days=7)
            date_from, date_to = s, s + timedelta(days=7)
        else:
            raise ValueError(f"Неизвестный период: {period}")

    rows = _read_rows(
        "WHERE date BETWEEN ? AND ?",
        (date_from.strftime("%Y-%m-%d"), date_to.strftime("%Y-%m-%d")),
    )

    return [ev for ev in rows if date_from <= ev["datetime"] < date_to]


def search_events(query: str):
    q = query.strip().lower()
    if len(q) < 3:
        return _read_rows("WHERE LOWER(text) LIKE ?", (f"%{q}%",))

    stem = q
    for suffix in (
        "иями", "ями", "ами", "ов", "ев", "ий", "ия", "ие", "ые", "ой",
        "ая", "ое", "ые", "ым", "им", "ах", "ях", "ам", "ям", "ом", "ем",
        "а", "я", "ы", "и", "о", "е", "у", "ю",
    ):
        if stem.endswith(suffix) and len(stem) - len(suffix) >= 3:
            stem = stem[:-len(suffix)]
            break

    return _read_rows(
        "WHERE LOWER(text) LIKE ?",
        (f"%{stem}%",),
    )


def run_scheduler():

    notified = _load_notified()

    while True:
        now = datetime.now().replace(second=0, microsecond=0)

        try:
            today = get_events("today")
        except Exception as e:
            print(f"[scheduler] ошибка чтения БД: {e}", flush=True)
            today = []

        changed = False

        for ev in today:
            if ev["id"] in notified:
                continue


            if ev["text"].endswith(" ✓"):
                continue


            if now <= ev["datetime"] <= now + timedelta(minutes=5):
                print(
                    f"\n🔔 {ev['datetime']:%H:%M} — {ev['text']}\n",
                    flush=True,
                )
                notified.add(ev["id"])
                changed = True

        if changed:
            _save_notified(notified)

        time.sleep(60)


def start_scheduler_in_thread():
    global _started
    if _started:
        return
    _started = True
    threading.Thread(target=run_scheduler, daemon=True).start()


if __name__ == "__main__":
    run_scheduler()