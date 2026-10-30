import math
import re
import sqlite3
from datetime import datetime

import scheduler
from embeddings import build_embedding_text

import os
import sys

if getattr(sys, 'frozen', False):
    # Папка: C:\Users\user\AppData\Roaming\DescVoice
    BASE_DIR = os.path.join(os.getenv('APPDATA'), "DescVoice")
    os.makedirs(BASE_DIR, exist_ok=True)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DB_PATH = os.path.join(BASE_DIR, "assistant.db")

RECORD_TYPES = {"meeting", "reminder", "task"}

DEFAULT_TOP_K = 5
MAX_TOP_K = 10
SEARCH_MIN_SCORE = 0.0

_TYPE_PREFIX_RE = re.compile(r"^\[(meeting|reminder|task)\]\s*")
_DONE_MARK = " ✓"


def parse_iso(value):
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone().replace(tzinfo=None)
    return parsed


def cosine(a, b):
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if not norm_a or not norm_b:
        return 0.0
    return dot / (norm_a * norm_b)


def encode_text(record_type, title, is_completed):
    text = f"[{record_type}] {title}"
    if is_completed:
        text += _DONE_MARK
    return text


def decode_text(text):
    is_completed = text.endswith(_DONE_MARK)
    if is_completed:
        text = text[: -len(_DONE_MARK)]
    m = _TYPE_PREFIX_RE.match(text)
    if m:
        record_type = m.group(1)
        title = text[m.end():]
    else:
        record_type = "task"
        title = text
    return record_type, title, is_completed


def dt_to_date_time(dt):
    if dt is None:
        return None, None
    return dt.strftime("%Y-%m-%d"), dt.strftime("%H:%M")


def vec_to_blob(vec):
    if vec is None:
        return None
    return ",".join(f"{x:.6f}" for x in vec).encode("ascii")


def blob_to_vec(blob):
    if not blob:
        return None
    try:
        return [float(x) for x in blob.decode("ascii").split(",") if x]
    except (ValueError, UnicodeDecodeError):
        return None


def row_to_record(row):
    record_id, date_s, time_s, text, embedding_blob = row
    record_type, title, is_completed = decode_text(text)
    if date_s:
        record_date = f"{date_s}T{time_s or '00:00'}:00"
    else:
        record_date = None
    return {
        "id": record_id,
        "type": record_type,
        "title": title,
        "date": record_date,
        "created_at": record_date,
        "is_completed": is_completed,
        "embedding": blob_to_vec(embedding_blob),
    }


def public(record):
    return {key: value for key, value in record.items() if key != "embedding"}


def error(message):
    return {"success": False, "error": message}


class SQLiteBackend:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self._ensure_schema()

    def _connect(self):
        return sqlite3.connect(self.db_path)

    def _ensure_schema(self):
        conn = self._connect()
        try:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS events ("
                "id INTEGER PRIMARY KEY, date TEXT, time TEXT, text TEXT)"
            )
            cols = {row[1] for row in conn.execute("PRAGMA table_info(events)")}
            if "embedding" not in cols:
                conn.execute("ALTER TABLE events ADD COLUMN embedding BLOB")
            conn.commit()
        finally:
            conn.close()

    def _insert(self, dt, text, embedding=None):
        conn = self._connect()
        try:
            cur = conn.execute(
                "INSERT INTO events (date, time, text, embedding) "
                "VALUES (?, ?, ?, ?)",
                (dt.strftime("%Y-%m-%d"), dt.strftime("%H:%M"),
                 text, vec_to_blob(embedding)),
            )
            conn.commit()
            return cur.lastrowid
        finally:
            conn.close()

    def _fetch_all(self):
        conn = self._connect()
        try:
            cur = conn.execute(
                "SELECT id, date, time, text, embedding "
                "FROM events ORDER BY date, time, id"
            )
            return cur.fetchall()
        finally:
            conn.close()

    def _fetch_one(self, record_id):
        conn = self._connect()
        try:
            cur = conn.execute(
                "SELECT id, date, time, text, embedding "
                "FROM events WHERE id = ?",
                (record_id,),
            )
            return cur.fetchone()
        finally:
            conn.close()

    def _update_row(self, record_id, date_s, time_s, text, embedding=None):
        conn = self._connect()
        try:
            conn.execute(
                "UPDATE events SET date = ?, time = ?, text = ?, embedding = ? "
                "WHERE id = ?",
                (date_s, time_s, text, vec_to_blob(embedding), record_id),
            )
            conn.commit()
        finally:
            conn.close()

    def _update_embedding(self, record_id, embedding):
        if embedding is None:
            return
        conn = self._connect()
        try:
            conn.execute(
                "UPDATE events SET embedding = ? WHERE id = ?",
                (vec_to_blob(embedding), record_id),
            )
            conn.commit()
        finally:
            conn.close()

    def delete_record(self, record_id):
        conn = self._connect()
        try:
            conn.execute("DELETE FROM events WHERE id = ?", (record_id,))
            conn.commit()
        finally:
            conn.close()

        return {
            "success": True,
            "record": {
                "id": record_id,
            },
        }

    def create_meeting(self, title, dt, embedder=None):
        embedding = None
        if embedder is not None:
            try:
                embedding = embedder.embed_document(
                    build_embedding_text("meeting", title)
                )
            except Exception as e:
                print(f"Эмбеддинг не посчитан: {e}")
        new_id = self._insert(
            dt, encode_text("meeting", title, False), embedding=embedding
        )
        return {"success": True, "id": new_id, "title": title,
                "datetime": dt.isoformat(timespec="minutes")}

    def create_reminder(self, text, dt, embedder=None):
        embedding = None
        if embedder is not None:
            try:
                embedding = embedder.embed_document(
                    build_embedding_text("reminder", text)
                )
            except Exception as e:
                print(f"Эмбеддинг не посчитан: {e}")
        new_id = self._insert(
            dt, encode_text("reminder", text, False), embedding=embedding
        )
        return {"success": True, "id": new_id, "text": text,
                "datetime": dt.isoformat(timespec="minutes")}

    def create_task(self, title, date=None, time=None, embedder=None):
        dt = datetime.now()
        if date:
            try:
                fmt = "%Y-%m-%d %H:%M" if time else "%Y-%m-%d"
                dt = datetime.strptime(f"{date} {time}" if time else date, fmt)
            except ValueError:
                pass
        embedding = None
        if embedder is not None:
            try:
                embedding = embedder.embed_document(
                    build_embedding_text("task", title)
                )
            except Exception as e:
                print(f"Эмбеддинг не посчитан: {e}")
        new_id = self._insert(
            dt, encode_text("task", title, False), embedding=embedding
        )
        return {"success": True, "id": new_id, "title": title,
                "datetime": dt.isoformat(timespec="minutes")}

    def list_events(self, period="today"):
        events = scheduler.get_events(period=period)
        return {
            "success": True,
            "period": period,
            "events": [
                {"id": e["id"],
                 "datetime": e["datetime"].isoformat(timespec="minutes"),
                 "text": e["text"]}
                for e in events
            ],
        }

    def search_events(self, query):
        events = scheduler.search_events(query)
        return {
            "success": True,
            "query": query,
            "events": [
                {"id": e["id"],
                 "datetime": e["datetime"].isoformat(timespec="minutes"),
                 "text": e["text"]}
                for e in events
            ],
        }

    def create_record(self, record_type, title, record_date,
                      created_at, is_completed, embedding=None):
        if record_date:
            dt = parse_iso(record_date)
        else:
            dt = datetime.now()

        date_str = dt.strftime("%Y-%m-%d")
        time_str = dt.strftime("%H:%M")
        full_text = encode_text(record_type, title, is_completed)

        conn = self._connect()
        try:
            cur_exact = conn.execute(
                "SELECT id FROM events WHERE date = ? AND time = ? AND text = ?",
                (date_str, time_str, full_text)
            )
            if cur_exact.fetchone() is not None:
                return {
                    "success": False,
                    "error": "Такая запись уже существует."
                }
            cur_time = conn.execute(
                "SELECT id, text FROM events WHERE date = ? AND time = ?",
                (date_str, time_str)
            )
            existing_time = cur_time.fetchone()
            if existing_time is not None:
                return {
                    "success": False,
                    "error": f"На {date_str} в {time_str} уже запланировано другое событие. Выберите другое время."
                }
        finally:
            conn.close()

        new_id = self._insert(
            dt,
            encode_text(record_type, title, is_completed),
            embedding=embedding,
        )
        record = {
            "id": new_id,
            "type": record_type,
            "title": title,
            "date": record_date,
            "created_at": created_at,
            "is_completed": is_completed,
        }
        return {"success": True, "record": record}
    def list_tasks(self):
        rows = self._fetch_all()
        return {
            "success": True,
            "records": [public(row_to_record(row)) for row in rows],
        }

    def get_record(self, record_id):
        row = self._fetch_one(record_id)
        if row is None:
            return None
        return row_to_record(row)

    def _filtered_records(self, record_type=None, date_from=None,
                          date_to=None, is_completed=None):
        matches = []
        for row in self._fetch_all():
            record = row_to_record(row)
            if record_type is not None and record["type"] != record_type:
                continue
            if is_completed is not None and record["is_completed"] != is_completed:
                continue
            if date_from is not None or date_to is not None:
                if record["date"] is None:
                    continue
                record_dt = parse_iso(record["date"])
                if date_from is not None and record_dt < date_from:
                    continue
                if date_to is not None and record_dt > date_to:
                    continue
            matches.append(record)
        return matches

    def search_records(self, query_embedding=None, record_type=None,
                       date_from=None, date_to=None, is_completed=None,
                       top_k=DEFAULT_TOP_K, min_score=SEARCH_MIN_SCORE):
        matches = self._filtered_records(
            record_type=record_type,
            date_from=date_from,
            date_to=date_to,
            is_completed=is_completed,
        )

        if query_embedding is not None:
            scored = []
            for record in matches:
                score = cosine(query_embedding, record.get("embedding"))
                if score < min_score:
                    continue
                item = public(record)
                item["score"] = round(score, 4)
                scored.append(item)
            scored.sort(key=lambda item: item["score"], reverse=True)
            return {
                "success": True,
                "total_found": len(scored),
                "records": scored[:top_k],
            }

        matches.sort(
            key=lambda r: (
                r["date"] is None,
                parse_iso(r["date"]) if r["date"] else datetime.max,
            )
        )
        return {
            "success": True,
            "total_found": len(matches),
            "records": [public(r) for r in matches[:top_k]],
        }

    def search_records_by_text(self, words, record_type=None,
                               date_from=None, date_to=None,
                               is_completed=None, top_k=DEFAULT_TOP_K):
        if not words:
            return {"success": True, "total_found": 0, "records": []}

        matches = self._filtered_records(
            record_type=record_type,
            date_from=date_from,
            date_to=date_to,
            is_completed=is_completed,
        )

        needle_words = [w.lower() for w in words]

        scored = []
        for record in matches:
            title_low = record["title"].lower()
            hits = sum(1 for w in needle_words if w in title_low)
            if hits == 0:
                continue
            item = public(record)
            item["score"] = round(hits / len(needle_words), 4)
            scored.append(item)

        scored.sort(
            key=lambda item: (
                -item["score"],
                item["date"] is None,
                parse_iso(item["date"]) if item["date"] else datetime.max,
            )
        )
        return {
            "success": True,
            "total_found": len(scored),
            "records": scored[:top_k],
        }

    def update_record(self, record_id, changes, embedding=None):
        row = self._fetch_one(record_id)
        if row is None:
            return error(f"Запись с id={record_id} не найдена.")

        record = row_to_record(row)
        new_type = changes.get("type", record["type"])
        new_title = changes.get("title", record["title"])
        new_completed = changes.get("is_completed", record["is_completed"])

        if "date" in changes:
            new_date = changes["date"]
        else:
            new_date = record["date"]

        if new_date:
            dt = parse_iso(new_date)
            date_s, time_s = dt_to_date_time(dt)
        else:
            date_s, time_s = None, None

        text = encode_text(new_type, new_title, new_completed)
        stored_embedding = record.get("embedding")
        final_embedding = embedding if embedding is not None else stored_embedding
        self._update_row(record_id, date_s, time_s, text, final_embedding)

        return {
            "success": True,
            "record": {
                "id": record_id,
                "type": new_type,
                "title": new_title,
                "date": new_date,
                "created_at": record["created_at"],
                "is_completed": new_completed,
            },
        }

    def backfill_embeddings(self, embedder):
        if embedder is None:
            return {"success": True, "updated": 0}
        updated = 0
        for row in self._fetch_all():
            record = row_to_record(row)
            if record.get("embedding") is not None:
                continue
            vec = embedder.embed_document(
                build_embedding_text(record["type"], record["title"])
            )
            if vec is not None:
                self._update_embedding(record["id"], vec)
                updated += 1
        return {"success": True, "updated": updated}