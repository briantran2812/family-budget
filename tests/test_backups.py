"""budget.db is copied aside before a new version migrates it (production safety, docs/DEPLOY.md F)."""
import os
import sqlite3
from datetime import datetime

import pytest

import backups
import db


@pytest.fixture
def data(tmp_path, monkeypatch):
    folder = tmp_path / "Application Support" / "ThuChiGiaDinh"  # the real path has a space
    folder.mkdir(parents=True)
    monkeypatch.setattr(db, "DB_PATH", folder / "budget.db")
    return folder


def add_tx(desc):
    with db.connect() as c:
        c.execute("INSERT INTO transactions(date, amount, description) VALUES ('2026-11-02', 45000, ?)", (desc,))


def test_first_start_makes_no_backup_and_records_version(data):
    backups.open_database("1.4.0")
    assert not (data / "backups").exists()
    with db.connect() as c:
        assert db.get_setting(c, "db_version") == "1.4.0"


def test_same_version_makes_no_backup(data):
    backups.open_database("1.4.0")
    add_tx("Phở")
    backups.open_database("1.4.0")
    assert not (data / "backups").exists()


def test_upgrade_backs_up_old_data_before_migrating(data):
    backups.open_database("1.4.0")
    add_tx("Phở bò")
    backups.open_database("1.4.1")
    backups.open_database("1.4.1")
    [saved] = (data / "backups").iterdir()  # one backup per upgrade, not per start
    assert saved.name.startswith("budget-1.4.0-")
    with sqlite3.connect(saved) as c:
        assert c.execute("SELECT description FROM transactions").fetchall() == [("Phở bò",)]
        assert c.execute("SELECT value FROM settings WHERE key = 'db_version'").fetchone() == ("1.4.0",)
    with db.connect() as c:
        assert db.get_setting(c, "db_version") == "1.4.1"


def test_backup_name_has_old_version_and_time(data):
    backups.open_database("1.4.0")
    saved = backups.backup_if_upgraded("1.4.1", now=datetime(2026, 11, 3, 21, 5))
    assert saved == data / "backups" / "budget-1.4.0-20261103-2105.db"


def test_database_from_before_1_4_is_named_after_last_seen_version(data):
    with sqlite3.connect(db.DB_PATH) as c:  # 1.3.0 wrote no db_version
        c.execute("CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT)")
        c.execute("INSERT INTO settings VALUES ('seen_version', '1.3.0')")
    assert backups.backup_if_upgraded("1.4.0").name.startswith("budget-1.3.0-")
    db.DB_PATH.unlink()
    sqlite3.connect(db.DB_PATH).execute("CREATE TABLE t (x)")
    assert backups.backup_if_upgraded("1.4.0").name.startswith("budget-unknown-")


def test_keeps_only_the_last_ten(data):
    backups.open_database("1.0.0")
    for i in range(12):
        saved = backups.backup_if_upgraded(f"9.{i}", now=datetime(2026, 11, 3, 21, i))
        os.utime(saved, (1_700_000_000 + i, 1_700_000_000 + i))  # in the past, oldest first
    names = sorted(p.name for p in (data / "backups").iterdir())
    assert names == [f"budget-1.0.0-20261103-21{i:02d}.db" for i in range(2, 12)]


def test_same_minute_is_numbered_not_overwritten(data):
    backups.open_database("1.0.0")
    when = datetime(2026, 11, 3, 21, 0)
    a, b = backups.backup_if_upgraded("2.0", now=when), backups.backup_if_upgraded("2.0", now=when)
    assert (a.name, b.name) == ("budget-1.0.0-20261103-2100.db", "budget-1.0.0-20261103-2100-2.db")


def test_failed_backup_still_opens_the_app(data, monkeypatch, capsys):
    backups.open_database("1.4.0")

    def boom(*a, **k):
        raise OSError("No space left on device")
    monkeypatch.setattr(backups, "backup_if_upgraded", boom)
    backups.open_database("1.4.1")
    assert "backup before upgrade failed" in capsys.readouterr().err
    with db.connect() as c:
        assert db.get_setting(c, "db_version") == "1.4.1"
