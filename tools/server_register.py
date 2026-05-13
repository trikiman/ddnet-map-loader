#!/usr/bin/env python3
"""Phase 2 — server-visibility layer for map sync.

Two pure functions:

  ensure_storage_cfg(ddnet_root, callback=None) -> dict
    Install or extend %APPDATA%\\DDNet\\storage.cfg so the DDNet server
    resolves maps from types/ recursively. Never overwrites existing lines;
    never overwrites an existing .bak.

  register_maps_in_db(ddnet_root, manifest, callback=None) -> dict
    Open ddnet-server.sqlite, take a hot VACUUM INTO backup, then
    INSERT OR IGNORE one row per map in `manifest` that does not already
    have a row in record_maps. Existing rows are preserved byte-identically.

Contracts:
  - No DELETE, no UPDATE against record_maps.
  - No reads or writes against record_race / record_teamrace / record_saves /
    record_points (or their _backup siblings).
  - No reads or writes against ddnet-cache.sqlite3.
"""

from __future__ import annotations

import os
import re
import shutil
import sqlite3
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Callable, Iterable

ProgressCallback = Callable[[dict[str, Any]], None]

STORAGE_CFG_FILENAME = "storage.cfg"
STORAGE_CFG_BACKUP_FILENAME = "storage.cfg.bak"
STORAGE_CFG_TARGET_LINE = "add_path $USERDIR/types"
STORAGE_CFG_DEFAULT_CONTENT = (
    "add_path $USERDIR\n"
    "add_path $DATADIR\n"
    "add_path $CURRENTDIR\n"
    "add_path $USERDIR/types\n"
)

RECORD_MAPS_TABLE = "record_maps"
SERVER_DB_FILENAME = "ddnet-server.sqlite"
BACKUP_PREFIX = ".ddnetcontrol-server-backup-"
BACKUP_RETAIN_COUNT = 3

# Tables we must never touch beyond record_maps; used in the post-write audit.
_TABLES_TO_LEAVE_ALONE = (
    "record_race", "record_race_backup",
    "record_teamrace", "record_teamrace_backup",
    "record_saves", "record_saves_backup",
    "record_points",
)


def _emit(callback: ProgressCallback | None, **payload: Any) -> None:
    if callback is not None:
        callback(payload)


# ---------------------------------------------------------------------------
# storage.cfg
# ---------------------------------------------------------------------------
def _strip_comment(line: str) -> str:
    """Strip DDNet-style comments from a config line. DDNet treats '#' and '//'
    as line comments (per upstream autoexec_server.cfg)."""
    for marker in ("#", "//"):
        idx = line.find(marker)
        if idx != -1:
            line = line[:idx]
    return line


def _normalize(line: str) -> str:
    return re.sub(r"\s+", " ", line.strip())


def _contains_target_line(content: str) -> bool:
    target_norm = _normalize(STORAGE_CFG_TARGET_LINE)
    for raw in content.splitlines():
        stripped = _strip_comment(raw)
        if _normalize(stripped) == target_norm:
            return True
    return False


def _atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    os.replace(tmp, path)


def ensure_storage_cfg(ddnet_root: Path, callback: ProgressCallback | None = None) -> dict[str, Any]:
    """Install or extend storage.cfg so DDNet's server finds types/.

    Returns a summary dict: {action, path, backup_path}.
      action in {"created", "appended", "no-op"}
    """
    cfg_path = ddnet_root / STORAGE_CFG_FILENAME
    backup_path = ddnet_root / STORAGE_CFG_BACKUP_FILENAME

    if not cfg_path.exists():
        _emit(callback, stage="storage_cfg", message=f"Creating {cfg_path} with recursive types/ path")
        _atomic_write_text(cfg_path, STORAGE_CFG_DEFAULT_CONTENT)
        return {"action": "created", "path": str(cfg_path), "backup_path": None}

    existing = cfg_path.read_text(encoding="utf-8")
    if _contains_target_line(existing):
        _emit(callback, stage="storage_cfg", message=f"{cfg_path} already has '{STORAGE_CFG_TARGET_LINE}', no-op")
        return {"action": "no-op", "path": str(cfg_path), "backup_path": None}

    # Append, backing up first (but never overwriting an existing .bak).
    if not backup_path.exists():
        shutil.copy2(cfg_path, backup_path)
    # Ensure trailing newline before appending
    new_content = existing
    if new_content and not new_content.endswith("\n"):
        new_content += "\n"
    new_content += STORAGE_CFG_TARGET_LINE + "\n"
    _atomic_write_text(cfg_path, new_content)
    _emit(callback, stage="storage_cfg",
          message=f"Appended '{STORAGE_CFG_TARGET_LINE}' to {cfg_path} (backup: {backup_path})")
    return {"action": "appended", "path": str(cfg_path), "backup_path": str(backup_path)}


# ---------------------------------------------------------------------------
# record_maps registration
# ---------------------------------------------------------------------------
def _backup_server_db(db_path: Path, callback: ProgressCallback | None) -> Path | None:
    """Take a VACUUM INTO backup of ddnet-server.sqlite. Keep BACKUP_RETAIN_COUNT
    most recent backups and delete the rest.

    Returns the path to the new backup (or None if backup is not possible).
    """
    if not db_path.exists():
        return None
    timestamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    backup_path = db_path.with_name(f"{BACKUP_PREFIX}{timestamp}.sqlite")
    try:
        conn = sqlite3.connect(str(db_path))
        try:
            # VACUUM INTO takes a consistent snapshot of the live DB.
            conn.execute("VACUUM INTO ?", (str(backup_path),))
        finally:
            conn.close()
    except sqlite3.Error as e:
        _emit(callback, stage="record_maps",
              message=f"VACUUM INTO backup failed: {e}; falling back to file copy")
        shutil.copy2(db_path, backup_path)

    # Rotate: keep BACKUP_RETAIN_COUNT most recent
    all_backups = sorted(
        db_path.parent.glob(f"{BACKUP_PREFIX}*.sqlite"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for old in all_backups[BACKUP_RETAIN_COUNT:]:
        try:
            old.unlink()
        except OSError:
            pass

    _emit(callback, stage="record_maps", message=f"DB snapshot: {backup_path}")
    return backup_path


def _collect_maps_from_types(types_root: Path) -> list[tuple[str, str]]:
    """Enumerate all .map files under types/ and return (category, stem) pairs.

    category is the first path component under types/ (e.g., 'novice', 'brutal',
    'testingmaps'). stem is the basename without '.map' extension — matches what
    the DDNet server uses as the map key.
    """
    if not types_root.exists():
        return []
    results: list[tuple[str, str]] = []
    for entry in types_root.rglob("*.map"):
        if not entry.is_file():
            continue
        rel = entry.relative_to(types_root)
        parts = rel.parts
        if len(parts) < 2:
            # Map file directly under types/ with no category — skip,
            # not something we can classify.
            continue
        category = parts[0]
        # Skip our own internal temp dirs
        if category.startswith(".") or category.startswith(".ddnetcontrol"):
            continue
        stem = entry.stem
        results.append((category, stem))
    return results


def _table_row_counts(conn: sqlite3.Connection, tables: Iterable[str]) -> dict[str, int | None]:
    counts: dict[str, int | None] = {}
    for t in tables:
        try:
            cur = conn.execute(f"SELECT COUNT(*) FROM {t}")
            counts[t] = cur.fetchone()[0]
        except sqlite3.OperationalError:
            counts[t] = None
    return counts


def register_maps_in_db(
    ddnet_root: Path,
    manifest: list[tuple[str, str]] | None = None,
    callback: ProgressCallback | None = None,
    server_alias_for_testingmaps: str = "testing",
) -> dict[str, Any]:
    """Register new maps in ddnet-server.sqlite's record_maps table.

    If `manifest` is None, enumerate from `types/`. Caller may pass a manifest
    directly (list of (category, stem) tuples) for performance.

    Returns summary dict with:
      path, rows_inserted, rows_already_present, rows_skipped_not_in_types,
      other_table_counts_unchanged (bool), backup_path
    """
    types_root = ddnet_root / "types"
    db_path = ddnet_root / SERVER_DB_FILENAME

    if not db_path.exists():
        _emit(callback, stage="record_maps", message=f"{db_path} missing, skipping registration")
        return {
            "path": str(db_path),
            "action": "skipped-no-db",
            "rows_inserted": 0,
            "rows_already_present": 0,
            "rows_skipped_not_in_types": 0,
            "other_table_counts_unchanged": True,
            "backup_path": None,
        }

    if manifest is None:
        manifest = _collect_maps_from_types(types_root)

    # De-dupe by stem (primary key of record_maps is Map alone). If the same
    # stem appears under multiple categories, keep the first — alphabetical
    # order by (category, stem) makes this deterministic and stable.
    seen_stems: set[str] = set()
    deduped: list[tuple[str, str]] = []
    duplicates_skipped = 0
    for cat, stem in sorted(manifest):
        if stem in seen_stems:
            duplicates_skipped += 1
            continue
        seen_stems.add(stem)
        deduped.append((cat, stem))

    backup_path = _backup_server_db(db_path, callback)

    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute("PRAGMA busy_timeout = 5000")
        pre_counts = _table_row_counts(conn, _TABLES_TO_LEAVE_ALONE)
        pre_record_maps = _table_row_counts(conn, [RECORD_MAPS_TABLE])[RECORD_MAPS_TABLE]

        rows_inserted = 0
        rows_already_present = 0

        conn.execute("BEGIN")
        for category, stem in deduped:
            server_val = server_alias_for_testingmaps if category == "testingmaps" else category
            cur = conn.execute(
                f"INSERT OR IGNORE INTO {RECORD_MAPS_TABLE} (Map, Server, Mapper, Points, Stars) "
                f"VALUES (?, ?, ?, ?, ?)",
                (stem, server_val, "Unknown", 0, 0),
            )
            if cur.rowcount == 1:
                rows_inserted += 1
            else:
                rows_already_present += 1
        conn.commit()

        post_counts = _table_row_counts(conn, _TABLES_TO_LEAVE_ALONE)
        post_record_maps = _table_row_counts(conn, [RECORD_MAPS_TABLE])[RECORD_MAPS_TABLE]

        other_unchanged = pre_counts == post_counts
        if not other_unchanged:
            # This should be impossible with only INSERT OR IGNORE on record_maps,
            # but assert it loudly if it happens.
            _emit(callback, stage="record_maps",
                  message=f"ALERT: other table counts changed! pre={pre_counts} post={post_counts}")
    finally:
        conn.close()

    result = {
        "path": str(db_path),
        "action": "ok",
        "rows_inserted": rows_inserted,
        "rows_already_present": rows_already_present,
        "rows_skipped_duplicate_stem": duplicates_skipped,
        "manifest_size": len(manifest),
        "record_maps_count_pre": pre_record_maps,
        "record_maps_count_post": post_record_maps,
        "other_table_counts_unchanged": other_unchanged,
        "other_table_counts": {"pre": pre_counts, "post": post_counts},
        "backup_path": str(backup_path) if backup_path else None,
    }
    _emit(callback, stage="record_maps",
          message=f"record_maps: +{rows_inserted} new rows, {rows_already_present} preserved, {duplicates_skipped} dupes skipped")
    return result


# ---------------------------------------------------------------------------
# Combined entry for sync_ddnet_maps to call
# ---------------------------------------------------------------------------
def register_with_server(
    ddnet_root: Path,
    callback: ProgressCallback | None = None,
) -> dict[str, Any]:
    """Convenience combiner used by sync_ddnet_maps when register_with_server=True."""
    cfg_summary = ensure_storage_cfg(ddnet_root, callback=callback)
    db_summary = register_maps_in_db(ddnet_root, manifest=None, callback=callback)
    return {"storage_cfg": cfg_summary, "record_maps": db_summary}


# ---------------------------------------------------------------------------
# CLI for manual use (not the canonical path; map_sync.py calls this module)
# ---------------------------------------------------------------------------
def main() -> int:
    import argparse
    import json
    import map_sync

    parser = argparse.ArgumentParser(description="Ensure storage.cfg + register synced maps in ddnet-server.sqlite")
    parser.add_argument("--ddnet-root", help="Override DDNet root (defaults to %%APPDATA%%\\DDNet)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done; DB backup still taken for parity")
    parser.add_argument("--json", action="store_true", help="Print summary as JSON to stdout; progress to stderr")
    args = parser.parse_args()

    ddnet_root = map_sync.get_ddnet_root(args.ddnet_root)

    def cli_progress(payload):
        stream = sys.stderr if args.json else sys.stdout
        print(f"[{payload.get('stage','reg')}] {payload.get('message','')}", file=stream)

    if args.dry_run:
        # Best-effort preview: report what ensure_storage_cfg WOULD do and what maps would be inserted.
        cfg_path = ddnet_root / STORAGE_CFG_FILENAME
        existing = cfg_path.read_text(encoding="utf-8") if cfg_path.exists() else ""
        if not cfg_path.exists():
            cfg_action = "created"
        elif _contains_target_line(existing):
            cfg_action = "no-op"
        else:
            cfg_action = "appended"
        manifest = _collect_maps_from_types(ddnet_root / "types")
        summary = {
            "storage_cfg": {"action": cfg_action, "path": str(cfg_path)},
            "record_maps": {"would_consider": len(manifest)},
            "dry_run": True,
        }
    else:
        summary = register_with_server(ddnet_root, callback=cli_progress)

    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        for k, v in summary.items():
            print(f"{k}: {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
