import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Tuple

DB_PATH = Path.home() / "waw_local.db"

def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS local_blinks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            count INTEGER NOT NULL,
            synced INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    return conn


def save_blink_locally(user_email: str, count: int) -> None:
    """Legacy single-blink insert. Prefer save_blinks_batch for better performance."""
    save_blinks_batch(user_email, [(None, count)])  # None timestamp will use datetime('now')


def save_blinks_batch(user_email: str, samples: List[Tuple[str | None, int]]) -> None:
    if not samples:
        return
    
    conn = _get_conn()
    cur = conn.cursor()
    
    # normalizinggg timestamps: use provided timestamp or current time
    now = datetime.now().isoformat()
    data = [
        (user_email, ts if ts is not None else now, count, 0)
        for ts, count in samples
    ]
    
    cur.executemany(
        "INSERT INTO local_blinks (user_email, timestamp, count, synced) "
        "VALUES (?, ?, ?, ?)",
        data,
    )
    
    conn.commit()
    conn.close()


def get_unsynced_blinks(user_email: str, limit: int = 500) -> List[Tuple[int, str, int]]:
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, timestamp, count FROM local_blinks "
        "WHERE user_email = ? AND synced = 0 ORDER BY id ASC LIMIT ?",
        (user_email, limit),
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def mark_blinks_synced(ids: list[int]) -> None:
    if not ids:
        return
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute(
        f"UPDATE local_blinks SET synced = 1 WHERE id IN ({','.join('?' for _ in ids)})",
        ids,
    )
    conn.commit()
    conn.close()