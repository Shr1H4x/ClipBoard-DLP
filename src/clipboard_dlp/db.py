from __future__ import annotations

import shutil
import sqlite3
import os
import glob
import threading
import time
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
            # POSIX-style permissions; skip on Windows where chmod semantics differ.
            if os.name != 'nt':
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
        # Safety net: back up the history once per day so an accidental wipe
        # (misclick, bug, test) can always be recovered.
        try:
            if self.count() > 0 and self._last_backup_age() > datetime.timedelta(days=1):
                self.backup()
        except Exception:
            pass

    @property
    def _backup_dir(self) -> str:
        # Backups live next to the database so isolated/test DBs never
        # pollute the real history's backup folder.
        return os.path.join(os.path.dirname(os.path.abspath(self.path)), "backups")

    def _last_backup_age(self) -> datetime.timedelta:
        """Age of the most recent backup file (infinite if none exists)."""
        os.makedirs(self._backup_dir, exist_ok=True)
        files = sorted(glob.glob(os.path.join(self._backup_dir, "history-*.db")))
        if not files:
            return datetime.timedelta.max
        mtime = os.path.getmtime(files[-1])
        return datetime.timedelta(seconds=time.time() - mtime)

    def backup(self) -> Optional[str]:
        """Snapshot the current history to backups/ and prune old snapshots.

        Returns the backup path, or None on failure. Never raises.
        """
        try:
            with self._lock:
                self._conn.commit()  # flush any pending writes
            os.makedirs(self._backup_dir, exist_ok=True)
            stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
            dest = os.path.join(self._backup_dir, f"history-{stamp}.db")
            shutil.copy2(self.path, dest)
            # keep the 10 most recent snapshots
            files = sorted(glob.glob(os.path.join(self._backup_dir, "history-*.db")))
            for stale in files[:-10]:
                try:
                    os.remove(stale)
                except Exception:
                    pass
            return dest
        except Exception:
            return None

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
        # Safety net: never destroy history without a recoverable snapshot.
        self.backup()
        with self._lock:
            self._conn.execute("DELETE FROM history")
            self._conn.commit()

    def count(self) -> int:
        with self._lock:
            return self._conn.execute("SELECT COUNT(*) FROM history").fetchone()[0]
