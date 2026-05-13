#!/usr/bin/env python3
"""Unit tests for tools/server_register.py — all I/O local, no network."""

from __future__ import annotations

import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import server_register as sr  # noqa: E402


DDNET_SERVER_SCHEMA = """
CREATE TABLE record_maps (
  Map VARCHAR(128) COLLATE BINARY NOT NULL,
  Server VARCHAR(32) COLLATE BINARY NOT NULL,
  Mapper VARCHAR(128) COLLATE BINARY NOT NULL,
  Points INT DEFAULT 0,
  Stars INT DEFAULT 0,
  Timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (Map)
);
CREATE TABLE record_race (
  Map VARCHAR(128) NOT NULL,
  Name VARCHAR(16) NOT NULL,
  Time FLOAT DEFAULT 0,
  PRIMARY KEY (Map, Name)
);
CREATE TABLE record_teamrace (
  Map VARCHAR(128) NOT NULL,
  Name VARCHAR(16) NOT NULL,
  Time FLOAT DEFAULT 0,
  ID BLOB NOT NULL,
  PRIMARY KEY (ID, Name)
);
CREATE TABLE record_saves (
  Savegame TEXT NOT NULL,
  Map VARCHAR(128) NOT NULL,
  Code VARCHAR(128) NOT NULL,
  PRIMARY KEY (Map, Code)
);
CREATE TABLE record_points (
  Name VARCHAR(16) NOT NULL,
  Points INT DEFAULT 0,
  PRIMARY KEY (Name)
);
CREATE TABLE record_race_backup (Map VARCHAR(128) NOT NULL, Name VARCHAR(16) NOT NULL, PRIMARY KEY (Map, Name));
CREATE TABLE record_teamrace_backup (Map VARCHAR(128) NOT NULL, Name VARCHAR(16) NOT NULL, ID BLOB NOT NULL, PRIMARY KEY (ID, Name));
CREATE TABLE record_saves_backup (Savegame TEXT NOT NULL, Map VARCHAR(128) NOT NULL, Code VARCHAR(128) NOT NULL, PRIMARY KEY (Map, Code));
"""


def _build_fake_ddnet_root(tmp: Path) -> Path:
    """Build a realistic %APPDATA%\\DDNet layout under tmp with a minimal server DB."""
    ddnet_root = tmp / "DDNet"
    (ddnet_root / "types").mkdir(parents=True)
    (ddnet_root / "maps").mkdir(parents=True)  # must remain untouched
    (ddnet_root / "downloadedmaps").mkdir(parents=True)  # must remain untouched
    # Seed an unrelated map in maps/ to audit later
    (ddnet_root / "maps" / "Tutorial.map").write_bytes(b"unrelated-user-map")
    # Create minimal server DB
    db = ddnet_root / sr.SERVER_DB_FILENAME
    conn = sqlite3.connect(str(db))
    try:
        conn.executescript(DDNET_SERVER_SCHEMA)
        # Pre-seed one user-populated row to test preservation.
        # Server='DDNet' is the canonical value — every record_maps row uses
        # it (see legacy %APPDATA%\DDNet\add_maps.ps1 upstream ships).
        conn.execute(
            "INSERT INTO record_maps (Map, Server, Mapper, Points, Stars) VALUES (?,?,?,?,?)",
            ("Kobra 4", "DDNet", "Ravie", 5, 3),
        )
        # Pre-seed rows in other tables we must leave alone
        conn.execute(
            "INSERT INTO record_race (Map, Name, Time) VALUES (?,?,?)",
            ("Kobra 4", "tester", 100.0),
        )
        conn.execute(
            "INSERT INTO record_points (Name, Points) VALUES (?,?)",
            ("tester", 150),
        )
        conn.commit()
    finally:
        conn.close()
    # Seed a cache sqlite that must also remain untouched
    cache = ddnet_root / "ddnet-cache.sqlite3"
    conn = sqlite3.connect(str(cache))
    try:
        conn.executescript(
            "CREATE TABLE server_pings (ip_address TEXT PRIMARY KEY, ping INTEGER NOT NULL, utc_timestamp TEXT NOT NULL);"
        )
        conn.execute("INSERT INTO server_pings VALUES (?,?,?)", ("1.2.3.4", 50, "2026-05-13"))
        conn.commit()
    finally:
        conn.close()
    return ddnet_root


class StorageCfgInstallTest(unittest.TestCase):
    def test_create_when_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ddnet_root = _build_fake_ddnet_root(Path(tmp))
            result = sr.ensure_storage_cfg(ddnet_root)
            self.assertEqual(result["action"], "created")
            cfg = ddnet_root / "storage.cfg"
            self.assertTrue(cfg.exists())
            content = cfg.read_text(encoding="utf-8")
            self.assertIn("add_path $USERDIR/types", content)
            self.assertIn("add_path $USERDIR\n", content)
            # No backup created when file was absent
            self.assertIsNone(result["backup_path"])

    def test_append_when_missing_line(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ddnet_root = _build_fake_ddnet_root(Path(tmp))
            cfg = ddnet_root / "storage.cfg"
            original = "add_path $USERDIR\nadd_path $DATADIR\n# some comment\nadd_path /some/other\n"
            cfg.write_text(original, encoding="utf-8")

            result = sr.ensure_storage_cfg(ddnet_root)
            self.assertEqual(result["action"], "appended")
            new_content = cfg.read_text(encoding="utf-8")
            # All target category lines must be present after append
            for target in sr.STORAGE_CFG_TARGET_LINES:
                self.assertIn(target, new_content)
            self.assertIn("# some comment", new_content)  # existing content preserved
            # Backup matches original
            backup = ddnet_root / "storage.cfg.bak"
            self.assertTrue(backup.exists())
            self.assertEqual(backup.read_text(encoding="utf-8"), original)

    def test_noop_when_line_already_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ddnet_root = _build_fake_ddnet_root(Path(tmp))
            cfg = ddnet_root / "storage.cfg"
            # Include all target lines with different whitespace and comments;
            # ensure_storage_cfg should recognize each and make no changes.
            target_block = "\n".join(
                f"  {line}   # category" for line in sr.STORAGE_CFG_TARGET_LINES
            )
            original = (
                "# ddnet storage config\n"
                "add_path $USERDIR\n"
                + target_block + "\n"
                "add_path $DATADIR\n"
            )
            cfg.write_text(original, encoding="utf-8")
            mtime_before = cfg.stat().st_mtime_ns

            result = sr.ensure_storage_cfg(ddnet_root)
            self.assertEqual(result["action"], "no-op")
            # File unchanged
            self.assertEqual(cfg.read_text(encoding="utf-8"), original)
            self.assertEqual(cfg.stat().st_mtime_ns, mtime_before)
            # No backup written
            self.assertFalse((ddnet_root / "storage.cfg.bak").exists())

    def test_never_overwrites_existing_backup(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ddnet_root = _build_fake_ddnet_root(Path(tmp))
            cfg = ddnet_root / "storage.cfg"
            backup = ddnet_root / "storage.cfg.bak"
            # Setup: user already has a backup from a prior edit
            cfg.write_text("add_path $USERDIR\n", encoding="utf-8")
            backup.write_text("PRECIOUS PRIOR BACKUP", encoding="utf-8")

            result = sr.ensure_storage_cfg(ddnet_root)
            self.assertEqual(result["action"], "appended")
            # Prior .bak unchanged
            self.assertEqual(backup.read_text(encoding="utf-8"), "PRECIOUS PRIOR BACKUP")


class RecordMapsRegistrationTest(unittest.TestCase):
    def test_inserts_new_rows_and_preserves_existing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ddnet_root = _build_fake_ddnet_root(Path(tmp))
            types_root = ddnet_root / "types"
            (types_root / "novice" / "maps").mkdir(parents=True)
            (types_root / "brutal" / "maps").mkdir(parents=True)
            # Kobra 4 is pre-seeded — existing row has Mapper='Ravie', Points=5
            (types_root / "novice" / "maps" / "Kobra 4.map").write_bytes(b"a")
            (types_root / "novice" / "maps" / "New Map One.map").write_bytes(b"b")
            (types_root / "brutal" / "maps" / "New Map Two.map").write_bytes(b"c")

            summary = sr.register_maps_in_db(ddnet_root)
            self.assertEqual(summary["action"], "ok")
            self.assertEqual(summary["rows_inserted"], 2)  # New Map One, New Map Two
            self.assertEqual(summary["rows_already_present"], 1)  # Kobra 4
            self.assertTrue(summary["other_table_counts_unchanged"])

            # Verify Kobra 4 row is byte-identical to what it was
            conn = sqlite3.connect(str(ddnet_root / sr.SERVER_DB_FILENAME))
            try:
                row = conn.execute(
                    "SELECT Map, Server, Mapper, Points, Stars FROM record_maps WHERE Map='Kobra 4'"
                ).fetchone()
            finally:
                conn.close()
            self.assertEqual(row, ("Kobra 4", "DDNet", "Ravie", 5, 3))

    def test_never_deletes_or_updates_existing_row(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ddnet_root = _build_fake_ddnet_root(Path(tmp))
            types_root = ddnet_root / "types"
            (types_root / "novice" / "maps").mkdir(parents=True)
            # Seed a .map file with the SAME name as the pre-seeded row, but
            # we expect the DB row (Ravie / 5 / 3) to stay intact even though
            # our code would default to Mapper='Unknown'/Points=0 for new rows.
            (types_root / "novice" / "maps" / "Kobra 4.map").write_bytes(b"x")

            summary = sr.register_maps_in_db(ddnet_root)
            self.assertEqual(summary["rows_inserted"], 0)
            self.assertEqual(summary["rows_already_present"], 1)

            conn = sqlite3.connect(str(ddnet_root / sr.SERVER_DB_FILENAME))
            try:
                row = conn.execute(
                    "SELECT Map, Server, Mapper, Points, Stars FROM record_maps WHERE Map='Kobra 4'"
                ).fetchone()
                # Also check record_race was untouched
                race_count = conn.execute("SELECT COUNT(*) FROM record_race").fetchone()[0]
            finally:
                conn.close()
            self.assertEqual(row, ("Kobra 4", "DDNet", "Ravie", 5, 3))
            self.assertEqual(race_count, 1)  # the Kobra 4 race row intact

    def test_all_inserted_rows_get_ddnet_server_value(self) -> None:
        """Every new row — regardless of source category — must be
        Server='DDNet'. DDNet's server uses the Server column when scoring
        and resolving votes; any other value breaks sv_map lookups."""
        with tempfile.TemporaryDirectory() as tmp:
            ddnet_root = _build_fake_ddnet_root(Path(tmp))
            types_root = ddnet_root / "types"
            (types_root / "novice" / "maps").mkdir(parents=True)
            (types_root / "brutal" / "maps").mkdir(parents=True)
            (types_root / "testingmaps" / "maps").mkdir(parents=True)
            (types_root / "novice" / "maps" / "Novice Map.map").write_bytes(b"a")
            (types_root / "brutal" / "maps" / "Brutal Map.map").write_bytes(b"b")
            (types_root / "testingmaps" / "maps" / "Beta Map.map").write_bytes(b"c")

            summary = sr.register_maps_in_db(ddnet_root)
            self.assertEqual(summary["rows_inserted"], 3)

            conn = sqlite3.connect(str(ddnet_root / sr.SERVER_DB_FILENAME))
            try:
                rows = conn.execute(
                    "SELECT Map, Server FROM record_maps "
                    "WHERE Map IN ('Novice Map', 'Brutal Map', 'Beta Map') "
                    "ORDER BY Map"
                ).fetchall()
            finally:
                conn.close()
            self.assertEqual(
                rows,
                [("Beta Map", "DDNet"), ("Brutal Map", "DDNet"), ("Novice Map", "DDNet")],
            )

    def test_skips_map_files_not_under_category_maps_subfolder(self) -> None:
        """Files directly under types/<category>/ (no maps/ subfolder) can't
        be resolved by DDNet's Storage layer, so they must be skipped — no
        row inserted for maps the server will never be able to load."""
        with tempfile.TemporaryDirectory() as tmp:
            ddnet_root = _build_fake_ddnet_root(Path(tmp))
            types_root = ddnet_root / "types"
            (types_root / "novice" / "maps").mkdir(parents=True)
            # .map file under maps/ — should be registered
            (types_root / "novice" / "maps" / "Valid.map").write_bytes(b"v")
            # .map file directly under category root — should be SKIPPED
            (types_root / "novice" / "Orphan.map").write_bytes(b"o")

            summary = sr.register_maps_in_db(ddnet_root)
            self.assertEqual(summary["rows_inserted"], 1)

            conn = sqlite3.connect(str(ddnet_root / sr.SERVER_DB_FILENAME))
            try:
                rows = conn.execute(
                    "SELECT Map FROM record_maps WHERE Map IN ('Valid', 'Orphan')"
                ).fetchall()
            finally:
                conn.close()
            self.assertEqual(rows, [("Valid",)])

    def test_dedupes_duplicate_stems_across_categories(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ddnet_root = _build_fake_ddnet_root(Path(tmp))
            types_root = ddnet_root / "types"
            (types_root / "novice" / "maps").mkdir(parents=True)
            (types_root / "brutal" / "maps").mkdir(parents=True)
            # Same stem in two categories — upstream guarantees this never happens
            # in practice, but guard against it deterministically.
            (types_root / "novice" / "maps" / "Shared.map").write_bytes(b"n")
            (types_root / "brutal" / "maps" / "Shared.map").write_bytes(b"b")

            summary = sr.register_maps_in_db(ddnet_root)
            self.assertEqual(summary["rows_inserted"], 1)
            self.assertEqual(summary["rows_skipped_duplicate_stem"], 1)

    def test_backup_is_taken_before_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ddnet_root = _build_fake_ddnet_root(Path(tmp))
            types_root = ddnet_root / "types"
            (types_root / "novice" / "maps").mkdir(parents=True)
            (types_root / "novice" / "maps" / "New.map").write_bytes(b"n")

            summary = sr.register_maps_in_db(ddnet_root)
            self.assertIsNotNone(summary["backup_path"])
            self.assertTrue(Path(summary["backup_path"]).exists())
            self.assertIn(sr.BACKUP_PREFIX, summary["backup_path"])


class NoOtherTablesTouchedTest(unittest.TestCase):
    def test_cache_sqlite_untouched(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ddnet_root = _build_fake_ddnet_root(Path(tmp))
            types_root = ddnet_root / "types"
            (types_root / "novice" / "maps").mkdir(parents=True)
            (types_root / "novice" / "maps" / "X.map").write_bytes(b"x")

            cache = ddnet_root / "ddnet-cache.sqlite3"
            import hashlib
            before = hashlib.sha256(cache.read_bytes()).hexdigest()

            sr.register_maps_in_db(ddnet_root)

            after = hashlib.sha256(cache.read_bytes()).hexdigest()
            self.assertEqual(before, after, "ddnet-cache.sqlite3 must not be modified")

    def test_maps_dir_untouched(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ddnet_root = _build_fake_ddnet_root(Path(tmp))
            types_root = ddnet_root / "types"
            (types_root / "novice" / "maps").mkdir(parents=True)
            (types_root / "novice" / "maps" / "X.map").write_bytes(b"x")

            tutorial = ddnet_root / "maps" / "Tutorial.map"
            tutorial_before_mtime = tutorial.stat().st_mtime_ns
            tutorial_before_bytes = tutorial.read_bytes()

            sr.register_maps_in_db(ddnet_root)

            self.assertEqual(tutorial.stat().st_mtime_ns, tutorial_before_mtime)
            self.assertEqual(tutorial.read_bytes(), tutorial_before_bytes)


if __name__ == "__main__":
    unittest.main(verbosity=2)
