from typing import Optional
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Tuple

DB_PATH = Path.home() / "waw_local.db"

def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT NOT NULL,
            name TEXT,
            start_time TEXT NOT NULL,
            end_time TEXT,
            synced INTEGER NOT NULL DEFAULT 0,
            cloud_session_id INTEGER,
            deleted INTEGER NOT NULL DEFAULT 0
        )
        """
    )

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

    # migrate existing table: add session_id column if it doesn't exist
    try:
        conn.execute("ALTER TABLE local_blinks ADD COLUMN session_id INTEGER")
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    return conn

def create_session(user_email: str, name: Optional[str] = None) -> int | None:
    """Create a new tracking session. Returns session_id."""
    conn = _get_conn()
    cur = conn.cursor()
    start_time = datetime.now().isoformat()
    cur.execute(
        "INSERT INTO sessions (user_email, name, start_time, synced, deleted) "
        "VALUES (?, ?, ?, 0, 0)",
        (user_email, name, start_time)
    )
    session_id = cur.lastrowid
    conn.commit()
    conn.close()
    return session_id if session_id else None


def end_session(session_id: int) -> None:
    """End a session by setting end_time."""
    conn = _get_conn()
    cur = conn.cursor()
    end_time = datetime.now().isoformat()
    cur.execute(
        "UPDATE sessions SET end_time = ? WHERE id = ?",
        (end_time, session_id)
    )
    conn.commit()
    conn.close()


def get_active_session(user_email: str) -> Optional[int]:
    """Get the active session_id for a user, or None if no active session."""
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT id FROM sessions "
        "WHERE user_email = ? AND end_time IS NULL AND deleted = 0 "
        "ORDER BY start_time DESC LIMIT 1",
        (user_email,)
    )
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None


def get_all_sessions(user_email: str) -> List[Tuple[int, Optional[str], str, Optional[str], int]]:
    """Get all sessions for a user. Returns list of (id, name, start_time, end_time, synced)."""
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, name, start_time, end_time, synced FROM sessions "
        "WHERE user_email = ? AND deleted = 0 "
        "ORDER BY start_time DESC",
        (user_email,)
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def get_session(session_id: int) -> Optional[Tuple[str, Optional[str], str, Optional[str], int]]:
    """Get a single session. Returns (user_email, name, start_time, end_time, synced) or None."""
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT user_email, name, start_time, end_time, synced FROM sessions "
        "WHERE id = ? AND deleted = 0",
        (session_id,)
    )
    row = cur.fetchone()
    conn.close()
    return row if row else None


def update_session_name(session_id: int, name: Optional[str]) -> None:
    """Update the name of a session."""
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute(
        "UPDATE sessions SET name = ? WHERE id = ?",
        (name, session_id)
    )
    conn.commit()
    conn.close()


def delete_session(session_id: int) -> None:
    """Mark a session as deleted (soft delete)."""
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute(
        "UPDATE sessions SET deleted = 1 WHERE id = ?",
        (session_id,)
    )
    conn.commit()
    conn.close()


def get_unsynced_sessions(user_email: str, limit: int = 50) -> List[Tuple[int, str, Optional[str], str, Optional[str]]]:
    """Get unsynced sessions. Returns list of (id, user_email, name, start_time, end_time)."""
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, user_email, name, start_time, end_time FROM sessions "
        "WHERE user_email = ? AND synced = 0 AND deleted = 0 "
        "ORDER BY id ASC LIMIT ?",
        (user_email, limit)
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def mark_session_synced(session_id: int, cloud_session_id: Optional[int] = None) -> None:
    """Mark a session as synced, optionally storing cloud_session_id."""
    conn = _get_conn()
    cur = conn.cursor()
    if cloud_session_id:
        cur.execute(
            "UPDATE sessions SET synced = 1, cloud_session_id = ? WHERE id = ?",
            (cloud_session_id, session_id)
        )
    else:
        cur.execute(
            "UPDATE sessions SET synced = 1 WHERE id = ?",
            (session_id,)
        )
    conn.commit()
    conn.close()


# ========== BLINK MANAGEMENT ==========

def save_blink_locally(user_email: str, count: int, session_id: Optional[int] = None) -> None:
    """Legacy single-blink insert. Prefer save_blinks_batch for better performance."""
    save_blinks_batch(user_email, [(None, count)], session_id)


def save_blinks_batch(user_email: str, samples: List[Tuple[str | None, int]], session_id: Optional[int] = None) -> None:
    """Save blink samples. If session_id is None, tries to get active session."""
    if not samples:
        return
    
    # If no session_id provided, try to get active session
    if session_id is None:
        session_id = get_active_session(user_email)
    
    conn = _get_conn()
    cur = conn.cursor()
    
    # Normalize timestamps: use provided timestamp or current time
    now = datetime.now().isoformat()
    data = [
        (user_email, ts if ts is not None else now, count, session_id, 0)
        for ts, count in samples
    ]
    
    cur.executemany(
        "INSERT INTO local_blinks (user_email, timestamp, count, session_id, synced) "
        "VALUES (?, ?, ?, ?, ?)",
        data,
    )
    
    conn.commit()
    conn.close()


def get_unsynced_blinks(user_email: str, limit: int = 500) -> List[Tuple[int, str, int, Optional[int]]]:
    """Get unsynced blinks. Returns list of (id, timestamp, count, session_id)."""
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, timestamp, count, session_id FROM local_blinks "
        "WHERE user_email = ? AND synced = 0 ORDER BY id ASC LIMIT ?",
        (user_email, limit),
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def get_blinks_for_session(session_id: int) -> List[Tuple[str, int]]:
    """Get all blinks for a session. Returns list of (timestamp, count)."""
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT timestamp, count FROM local_blinks "
        "WHERE session_id = ? ORDER BY timestamp ASC",
        (session_id,)
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def mark_blinks_synced(ids: list[int]) -> None:
    """Mark blinks as synced."""
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