from __future__ import annotations

import sqlite3
import os
import threading
import datetime
from typing import Optional

from .constants import DB_PATH


class ClipDB:
    def __init__(self, path=DB_PATH):
        self.path  = path
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._init()
        # Restrict DB file permissions to owner-read/write where supported.
        try:
            os.chmod(self.path, 0o600)
        except Exception:
            # Best-effort; ignore failures on platforms that don't support chmod.
            pass

    def _init(self):
        with self._lock:
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS history (
                    id        INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT    NOT NULL,
                    content   TEXT    NOT NULL,
                    source    TEXT
                )
            """)
            # Ensure older DBs get the new column
            try:
                cols = [c[1] for c in self._conn.execute("PRAGMA table_info(history)").fetchall()]
                if 'source' not in cols:
                    self._conn.execute("ALTER TABLE history ADD COLUMN source TEXT")
            except Exception:
                pass
            self._conn.commit()

    def add(self, text: str, source: str | None = None) -> int:
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self._lock:
            cur = self._conn.execute(
                "INSERT INTO history (timestamp,content,source) VALUES (?,?,?)", (ts, text, source))
            self._conn.commit()
            return cur.lastrowid

    def list(self, limit=300):
        with self._lock:
            return self._conn.execute(
                "SELECT id,timestamp,content,source FROM history ORDER BY id DESC LIMIT ?",
                (limit,)).fetchall()

    def last(self) -> Optional[str]:
        with self._lock:
            r = self._conn.execute(
                "SELECT content FROM history ORDER BY id DESC LIMIT 1").fetchone()
            return r[0] if r else None

    def reset_sequence(self):
        with self._lock:
            try:
                self._conn.execute("DELETE FROM sqlite_sequence WHERE name='history'")
                self._conn.commit()
            except Exception:
                try:
                    self._conn.execute("VACUUM")
                    self._conn.commit()
                except Exception:
                    pass

    def get(self, rid) -> Optional[str]:
        with self._lock:
            r = self._conn.execute("SELECT content FROM history WHERE id=?", (rid,)).fetchone()
            return r[0] if r else None

    def get_source(self, rid) -> Optional[str]:
        with self._lock:
            try:
                r = self._conn.execute("SELECT source FROM history WHERE id=?", (rid,)).fetchone()
                return r[0] if r else None
            except Exception:
                return None

    def get_record(self, rid):
        """Return full record tuple (id, timestamp, content, source) or None."""
        with self._lock:
            r = self._conn.execute("SELECT id,timestamp,content,source FROM history WHERE id=?", (rid,)).fetchone()
            return r

    def delete(self, rid):
        with self._lock:
            self._conn.execute("DELETE FROM history WHERE id=?", (rid,))
            self._conn.commit()

    def clear(self):
        with self._lock:
            self._conn.execute("DELETE FROM history")
            self._conn.commit()

    def count(self) -> int:
       with self._lock:
            return self._conn.execute("SELECT COUNT(*) FROM history").fetchone()[0]
