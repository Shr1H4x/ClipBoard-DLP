import glob
import os
import sqlite3

from clipboard_dlp.db import ClipDB


def test_clear_creates_recoverable_backup(tmp_path):
    db_file = str(tmp_path / "history.db")
    db = ClipDB(db_file)
    db.add("precious-data-1")
    db.add("precious-data-2")
    db.clear()

    snapshots = sorted(glob.glob(str(tmp_path / "backups" / "history-*.db")))
    assert snapshots, "clear() must snapshot the DB before wiping"

    rows = [r[0] for r in sqlite3.connect(snapshots[-1]).execute("SELECT content FROM history")]
    assert "precious-data-1" in rows
    assert "precious-data-2" in rows
    assert db.count() == 0


def test_backup_prunes_old_snapshots(tmp_path):
    db_file = str(tmp_path / "history.db")
    db = ClipDB(db_file)
    for i in range(15):
        db.add(f"row-{i}")
        db.backup()
    snapshots = glob.glob(str(tmp_path / "backups" / "history-*.db"))
    assert len(snapshots) <= 10


def test_isolated_db_backups_stay_next_to_it(tmp_path):
    # Backups must follow the DB file, never the default XDG location.
    db_dir = tmp_path / "custom"
    db_dir.mkdir()
    db_file = str(db_dir / "history.db")
    db = ClipDB(db_file)
    db.add("row")
    db.backup()
    assert glob.glob(str(db_dir / "backups" / "*.db"))
