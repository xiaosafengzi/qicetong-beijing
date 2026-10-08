from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"


def runtime_dir() -> Path:
    path = Path(os.environ.get("QCT_RUNTIME", str(ROOT / "runtime")))
    path.mkdir(parents=True, exist_ok=True)
    return path


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def connection():
    con = sqlite3.connect(runtime_dir() / "qicetong.sqlite3", timeout=20)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def initialize():
    with connection() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS entities (kind TEXT, id TEXT, payload TEXT NOT NULL,
            updated_at TEXT NOT NULL, PRIMARY KEY(kind,id));
        CREATE TABLE IF NOT EXISTS events (id TEXT PRIMARY KEY, action TEXT NOT NULL,
            target TEXT NOT NULL, detail TEXT NOT NULL, created_at TEXT NOT NULL);
        """)
    for path, kind in [(DATA / "policies.json", "policy"), (DATA / "companies.json", "company")]:
        if path.exists():
            for item in json.loads(path.read_text(encoding="utf-8")):
                with connection() as con:
                    con.execute("INSERT OR IGNORE INTO entities VALUES (?,?,?,?)",
                                (kind, item["id"], json.dumps(item, ensure_ascii=False), now()))


def put(kind: str, item: dict) -> dict:
    with connection() as con:
        con.execute("INSERT INTO entities VALUES (?,?,?,?) ON CONFLICT(kind,id) DO UPDATE SET payload=excluded.payload,updated_at=excluded.updated_at",
                    (kind, item["id"], json.dumps(item, ensure_ascii=False, allow_nan=False), now()))
    return item


def get(kind: str, entity_id: str) -> dict:
    with connection() as con:
        row = con.execute("SELECT payload FROM entities WHERE kind=? AND id=?", (kind, entity_id)).fetchone()
    if not row:
        raise KeyError(f"找不到 {kind}: {entity_id}")
    return json.loads(row["payload"])


def all_items(kind: str) -> list[dict]:
    with connection() as con:
        rows = con.execute("SELECT payload FROM entities WHERE kind=? ORDER BY rowid", (kind,)).fetchall()
    return [json.loads(r["payload"]) for r in rows]


def event(action: str, target: str, detail: dict):
    with connection() as con:
        con.execute("INSERT INTO events VALUES (?,?,?,?,?)",
                    (uuid4().hex, action, target, json.dumps(detail, ensure_ascii=False), now()))


def events() -> list[dict]:
    with connection() as con:
        return [dict(r) for r in con.execute("SELECT * FROM events ORDER BY created_at DESC LIMIT 100")]
