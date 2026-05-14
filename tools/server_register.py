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
# DDNet's storage subsystem (src/engine/shared/storage.cpp) has two crucial
# constraints for our "show category maps on server" use case:
#
#  1. AddPath() treats $USERDIR/$DATADIR/$CURRENTDIR as STANDALONE tokens,
#     not prefixes. Writing "add_path $USERDIR/types/oldschool" fails with
#     "cannot add path which is not a directory" because the server literally
#     tries to open a path named "$USERDIR/types/oldschool". We therefore
#     emit absolute paths for per-category entries.
#
#  2. MAX_PATHS = 16. The first 3 slots go to $USERDIR / $DATADIR /
#     $CURRENTDIR (the defaults), leaving 13 category slots. We order the
#     category list so the categories the user actually plays (novice +
#     brutal + testingmaps) are always in the first 13 even if we need to
#     truncate.
#
#  3. CServer::LoadMap() prepends "maps/" to the map name, so every
#     add_path must point at a directory that CONTAINS a "maps/" subfolder.
#     Upstream's types/novice/, types/oldschool/ etc. all do, and our
#     sync_testing_maps writes to types/testingmaps/maps/.
DDNET_MAX_PATHS = 16
STORAGE_CFG_BASE_LINES = (
    "add_path $USERDIR",
    "add_path $DATADIR",
    "add_path $CURRENTDIR",
)
# Combined-maps category. We hardlink every .map from every other category
# into types/_all/maps/<stem>.map and only emit one add_path for it. That
# sidesteps DDNet's MAX_PATHS=16 limit and lets every synced map load
# regardless of source category.
COMBINED_CATEGORY = "_all"
# Order matters when truncating to fit MAX_PATHS, but with the combined
# strategy we typically only emit one entry. Per-category fallbacks remain
# in the list so callers that opt out of the combined dir (or run on an
# install where hardlinks fail) still get coverage.
STORAGE_CFG_CATEGORIES = (
    COMBINED_CATEGORY,
    "testingmaps",
    "novice", "moderate", "brutal", "insane",
    "oldschool", "solo", "race",
    "dummy",
    "ddmax.easy", "ddmax.next", "ddmax.pro", "ddmax.nut",
    "fun", "event",
)


def _build_storage_cfg_target_lines(ddnet_root: Path) -> list[str]:
    """Return the list of `add_path ...` lines for the given DDNet root,
    truncated to DDNET_MAX_PATHS - len(BASE_LINES) entries.

    When `types/_all/maps/` exists and is non-empty, we use only it — that
    one path covers every map across every category and lets us stay well
    under DDNet's MAX_PATHS=16 limit. Otherwise we fall back to per-category
    add_paths (also truncated to fit MAX_PATHS).
    """
    types_root = ddnet_root / "types"
    max_categories = DDNET_MAX_PATHS - len(STORAGE_CFG_BASE_LINES)

    combined_dir = types_root / COMBINED_CATEGORY / "maps"
    if combined_dir.is_dir() and any(combined_dir.glob("*.map")):
        return [f"add_path {(types_root / COMBINED_CATEGORY).as_posix()}"]

    lines: list[str] = []
    for cat in STORAGE_CFG_CATEGORIES:
        if cat == COMBINED_CATEGORY:
            continue
        if len(lines) >= max_categories:
            break
        cat_dir = types_root / cat
        if cat_dir.is_dir():
            lines.append(f"add_path {cat_dir.as_posix()}")
    return lines


def rebuild_combined_maps_dir(
    types_root: Path,
    callback: ProgressCallback | None = None,
) -> dict[str, Any]:
    """Rebuild `types/_all/maps/` so it contains a hardlink (or copy fallback)
    of every .map file from every other category under `types/<cat>/maps/`.

    This lets a single `add_path .../types/_all` line in storage.cfg cover
    every map regardless of source category, sidestepping DDNet's hardcoded
    MAX_PATHS=16 limit.

    Idempotent: existing hardlinks are kept when their inode already matches
    the source. Stale combined entries (whose source disappeared) are
    removed. When two categories share a map stem, the alphabetically first
    category wins (deterministic).
    """
    combined_root = types_root / COMBINED_CATEGORY
    combined_dir = combined_root / "maps"

    if not types_root.exists():
        return {"action": "skipped-no-types", "linked": 0, "skipped": 0, "removed": 0, "total": 0}

    combined_dir.mkdir(parents=True, exist_ok=True)

    # Enumerate every <category>/maps/<stem>.map under types/
    sources: dict[str, Path] = {}
    for entry in sorted(types_root.rglob("*.map")):
        if not entry.is_file():
            continue
        rel = entry.relative_to(types_root)
        parts = rel.parts
        if len(parts) < 3 or parts[1] != "maps":
            continue
        category = parts[0]
        # Skip our own combined dir and any hidden/state dirs.
        if category == COMBINED_CATEGORY or category.startswith("."):
            continue
        # Dedupe by stem: first category wins (rglob+sorted gives stable order).
        if entry.stem in sources:
            continue
        sources[entry.stem] = entry

    existing = {p.stem: p for p in combined_dir.glob("*.map") if p.is_file()}

    linked = 0
    skipped_unchanged = 0
    refreshed = 0
    fallback_copied = 0
    removed = 0

    for stem, src in sources.items():
        dst = combined_dir / f"{stem}.map"
        if dst.exists():
            # Same inode? Hardlink already current — leave it alone.
            try:
                if dst.stat().st_ino == src.stat().st_ino and dst.stat().st_dev == src.stat().st_dev:
                    skipped_unchanged += 1
                    continue
            except OSError:
                pass
            # Stale link or copy — drop and recreate.
            try:
                dst.unlink()
            except OSError:
                continue
            refreshed += 1
        try:
            os.link(src, dst)
            linked += 1
        except OSError:
            # Cross-volume or filesystem refused hardlinks — fall back to copy.
            try:
                shutil.copy2(src, dst)
                fallback_copied += 1
                linked += 1
            except OSError:
                pass

    # Drop orphans whose source no longer exists.
    source_stems = set(sources)
    for stem, path in existing.items():
        if stem not in source_stems:
            try:
                path.unlink()
                removed += 1
            except OSError:
                pass

    summary = {
        "action": "ok",
        "combined_dir": str(combined_dir),
        "total_sources": len(sources),
        "linked": linked,
        "skipped_unchanged": skipped_unchanged,
        "refreshed": refreshed,
        "fallback_copied": fallback_copied,
        "removed": removed,
    }
    _emit(
        callback,
        stage="combined_maps",
        message=(
            f"Combined dir: {linked} linked ({fallback_copied} via copy fallback), "
            f"{skipped_unchanged} unchanged, {removed} orphans removed; "
            f"{len(sources)} maps total"
        ),
        counts={
            "linked": linked,
            "unchanged": skipped_unchanged,
            "removed": removed,
            "total": len(sources),
        },
    )
    return summary


def _build_storage_cfg_content(ddnet_root: Path) -> str:
    target_lines = _build_storage_cfg_target_lines(ddnet_root)
    using_combined = (
        len(target_lines) == 1
        and target_lines[0].endswith(f"/types/{COMBINED_CATEGORY}")
    )
    if using_combined:
        header = (
            "####\n"
            "# Written by ddnetcontrol.\n"
            "# Single combined-maps add_path covers every category by way of\n"
            "# hardlinks (or copies) under types/_all/maps/. Stays well under\n"
            "# DDNet's MAX_PATHS=16 limit.\n"
            "####\n\n"
        )
    else:
        header = (
            "####\n"
            "# Written by ddnetcontrol.\n"
            "# DDNet's Storage AddPath requires $USERDIR/$DATADIR/$CURRENTDIR as\n"
            "# STANDALONE tokens, not prefixes. Use absolute paths for per-category\n"
            "# maps. MAX_PATHS is 16, so at most 13 category entries fit.\n"
            "####\n\n"
        )
    lines = list(STORAGE_CFG_BASE_LINES) + target_lines
    return header + "\n".join(lines) + "\n"


# Recognized header prefix for files we previously wrote — when we see this
# in an existing storage.cfg we know it's safe to rewrite to canonical form.
_DDNETCONTROL_HEADER_MARKER = "# Written by ddnetcontrol"
_DDNETCONTROL_LEGACY_HEADER_MARKER = "# Rewritten by ddnetcontrol"

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


def _contains_line(content: str, target_line: str) -> bool:
    target_norm = _normalize(target_line)
    for raw in content.splitlines():
        stripped = _strip_comment(raw)
        if _normalize(stripped) == target_norm:
            return True
    return False


def _missing_target_lines(content: str, target_lines: list[str] | tuple[str, ...]) -> list[str]:
    return [line for line in target_lines if not _contains_line(content, line)]


def _atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    os.replace(tmp, path)


def ensure_storage_cfg(
    ddnet_root: Path,
    callback: ProgressCallback | None = None,
    storage_cfg_path: Path | None = None,
) -> dict[str, Any]:
    """Install or extend storage.cfg so DDNet's server finds types/ category maps.

    `ddnet_root` is the user-data root (typically `%APPDATA%\\DDNet`) — the
    location whose `types/<category>/maps/` will be referenced from the cfg.

    `storage_cfg_path` is where the storage.cfg file lives. When omitted it
    defaults to `<ddnet_root>/storage.cfg`, but DDNet's server reads its
    storage.cfg from `$CURRENTDIR` (the directory it's started from). For
    Steam-installed servers that's the install folder, NOT %APPDATA%, so
    callers wiring the integration should pass the install dir explicitly.

    Returns a summary dict: {action, path, backup_path, added_lines}.
      action in {"created", "appended", "no-op"}
    """
    cfg_path = storage_cfg_path if storage_cfg_path is not None else (ddnet_root / STORAGE_CFG_FILENAME)
    backup_path = cfg_path.with_suffix(cfg_path.suffix + ".bak") if cfg_path.suffix else cfg_path.with_name(cfg_path.name + ".bak")
    target_lines = _build_storage_cfg_target_lines(ddnet_root)

    if not cfg_path.exists():
        full_content = _build_storage_cfg_content(ddnet_root)
        _emit(callback, stage="storage_cfg",
              message=f"Creating {cfg_path} with {len(target_lines)} type add_path entries")
        _atomic_write_text(cfg_path, full_content)
        return {
            "action": "created",
            "path": str(cfg_path),
            "backup_path": None,
            "added_lines": target_lines,
        }

    existing = cfg_path.read_text(encoding="utf-8")
    is_ours = (
        _DDNETCONTROL_HEADER_MARKER in existing
        or _DDNETCONTROL_LEGACY_HEADER_MARKER in existing
    )
    expected_content = _build_storage_cfg_content(ddnet_root)
    if is_ours and existing != expected_content:
        # Rewrite to canonical form (handles cases like switching from per-
        # category mode to combined mode after _all/maps/ gets populated).
        if not backup_path.exists():
            shutil.copy2(cfg_path, backup_path)
        _atomic_write_text(cfg_path, expected_content)
        _emit(callback, stage="storage_cfg",
              message=f"Rewrote {cfg_path} to canonical form ({len(target_lines)} category line(s))")
        return {
            "action": "rewritten",
            "path": str(cfg_path),
            "backup_path": str(backup_path),
            "added_lines": target_lines,
        }
    missing = _missing_target_lines(existing, target_lines)
    if not missing:
        _emit(callback, stage="storage_cfg",
              message=f"{cfg_path} already has all {len(target_lines)} type add_path entries, no-op")
        return {
            "action": "no-op",
            "path": str(cfg_path),
            "backup_path": None,
            "added_lines": [],
        }

    # Append missing lines. Back up the original first (but never overwrite
    # an existing .bak, so we don't clobber a prior user backup).
    if not backup_path.exists():
        shutil.copy2(cfg_path, backup_path)
    new_content = existing
    if new_content and not new_content.endswith("\n"):
        new_content += "\n"
    new_content += "\n".join(missing) + "\n"
    _atomic_write_text(cfg_path, new_content)
    _emit(callback, stage="storage_cfg",
          message=f"Appended {len(missing)} missing add_path line(s) to {cfg_path} (backup: {backup_path})")
    return {
        "action": "appended",
        "path": str(cfg_path),
        "backup_path": str(backup_path),
        "added_lines": missing,
    }


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

    Skips files directly under a category root: the DDNet server only resolves
    maps via `<add_path>/maps/<stem>.map`, so .map files that aren't under a
    `maps/` subfolder of their category can't be loaded anyway.
    """
    if not types_root.exists():
        return []
    results: list[tuple[str, str]] = []
    for entry in types_root.rglob("*.map"):
        if not entry.is_file():
            continue
        rel = entry.relative_to(types_root)
        parts = rel.parts
        # Expect shape: <category>/maps/<stem>.map (at least three parts).
        # Category configs like types/novice/flexreset.cfg don't matter here.
        if len(parts) < 3 or parts[1] != "maps":
            continue
        category = parts[0]
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


RECORD_MAPS_SERVER_VALUE = "DDNet"


def register_maps_in_db(
    ddnet_root: Path,
    manifest: list[tuple[str, str]] | None = None,
    callback: ProgressCallback | None = None,
) -> dict[str, Any]:
    """Register new maps in ddnet-server.sqlite's record_maps table.

    If `manifest` is None, enumerate from `types/`. Caller may pass a manifest
    directly (list of (category, stem) tuples) for performance.

    Every inserted row uses `Server='DDNet'` — this matches DDNet's server
    convention (see the legacy `%APPDATA%\\DDNet\\add_maps.ps1` script
    upstream ships). Rows with other Server values cause sv_map lookups to
    fail because the server matches on (Map, Server) when scoring.

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
        for _category, stem in deduped:
            cur = conn.execute(
                f"INSERT OR IGNORE INTO {RECORD_MAPS_TABLE} (Map, Server, Mapper, Points, Stars) "
                f"VALUES (?, ?, ?, ?, ?)",
                (stem, RECORD_MAPS_SERVER_VALUE, "Unknown", 0, 0),
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


def repair_server_column(
    ddnet_root: Path,
    callback: ProgressCallback | None = None,
) -> dict[str, Any]:
    """Opt-in one-time repair for rows with a wrong Server value.

    Prior buggy versions of this module inserted record_maps rows with
    Server=<category> (e.g. 'novice', 'brutal') or Server='testing', which
    breaks DDNet's sv_map resolution — it expects Server='DDNet' for every
    row (matching the legacy add_maps.ps1 upstream convention).

    This repair updates ONLY rows where:
      1. Server != 'DDNet' (so user's own rows that happen to use a different
         value aren't mutated), AND
      2. Map matches a stem we just synced under types/<category>/maps/
         (so rows for maps the user manually added or that came from a
         different source are never touched).

    A backup is taken before the UPDATE runs, same as register_maps_in_db.
    """
    db_path = ddnet_root / SERVER_DB_FILENAME
    types_root = ddnet_root / "types"
    if not db_path.exists():
        return {"action": "skipped-no-db", "rows_updated": 0, "backup_path": None}

    manifest = _collect_maps_from_types(types_root)
    our_stems = {stem for _cat, stem in manifest}
    if not our_stems:
        _emit(callback, stage="repair_server",
              message="No maps found under types/, nothing to repair")
        return {"action": "no-op-empty-manifest", "rows_updated": 0, "backup_path": None}

    backup_path = _backup_server_db(db_path, callback)
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute("PRAGMA busy_timeout = 5000")
        # Find rows that would be affected so we can log before the write.
        placeholders = ",".join("?" * len(our_stems))
        victims = conn.execute(
            f"SELECT Map, Server FROM {RECORD_MAPS_TABLE} "
            f"WHERE Server != ? AND Map IN ({placeholders})",
            (RECORD_MAPS_SERVER_VALUE, *sorted(our_stems)),
        ).fetchall()
        if not victims:
            _emit(callback, stage="repair_server",
                  message=f"No rows need repair (all {len(our_stems)} our-maps rows already have Server='DDNet' or don't exist)")
            return {
                "action": "no-op-none-broken",
                "rows_updated": 0,
                "backup_path": str(backup_path) if backup_path else None,
                "checked_stems": len(our_stems),
            }

        _emit(callback, stage="repair_server",
              message=f"Updating {len(victims)} row(s) Server -> 'DDNet'")
        conn.execute("BEGIN")
        cur = conn.execute(
            f"UPDATE {RECORD_MAPS_TABLE} SET Server = ? "
            f"WHERE Server != ? AND Map IN ({placeholders})",
            (RECORD_MAPS_SERVER_VALUE, RECORD_MAPS_SERVER_VALUE, *sorted(our_stems)),
        )
        conn.commit()
        rows_updated = cur.rowcount
    finally:
        conn.close()

    return {
        "action": "ok",
        "rows_updated": rows_updated,
        "backup_path": str(backup_path) if backup_path else None,
        "checked_stems": len(our_stems),
        "victims_preview": [{"Map": m, "Server": s} for m, s in victims[:10]],
    }


# ---------------------------------------------------------------------------
# Combined entry for sync_ddnet_maps to call
# ---------------------------------------------------------------------------
def register_with_server(
    ddnet_root: Path,
    callback: ProgressCallback | None = None,
    storage_cfg_path: Path | None = None,
) -> dict[str, Any]:
    """Convenience combiner used by sync_ddnet_maps when register_with_server=True."""
    combined_summary = rebuild_combined_maps_dir(ddnet_root / "types", callback=callback)
    cfg_summary = ensure_storage_cfg(ddnet_root, callback=callback, storage_cfg_path=storage_cfg_path)
    db_summary = register_maps_in_db(ddnet_root, manifest=None, callback=callback)
    return {
        "combined_maps": combined_summary,
        "storage_cfg": cfg_summary,
        "record_maps": db_summary,
    }


# ---------------------------------------------------------------------------
# CLI for manual use (not the canonical path; map_sync.py calls this module)
# ---------------------------------------------------------------------------
def main() -> int:
    import argparse
    import json
    import map_sync

    parser = argparse.ArgumentParser(description="Ensure storage.cfg + register synced maps in ddnet-server.sqlite")
    parser.add_argument("--ddnet-root", help="Override DDNet root (defaults to %%APPDATA%%\\DDNet)")
    parser.add_argument(
        "--storage-cfg",
        help="Override storage.cfg target path. DDNet's server reads its storage.cfg from "
             "$CURRENTDIR (the directory it's launched from). For Steam-installed servers "
             "that's the install folder. Pass the install dir's storage.cfg here so the "
             "running server actually picks up our category add_paths.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done; DB backup still taken for parity")
    parser.add_argument("--json", action="store_true", help="Print summary as JSON to stdout; progress to stderr")
    parser.add_argument(
        "--repair-server-column",
        action="store_true",
        help="One-time repair: UPDATE record_maps rows where Server != 'DDNet' AND Map is one we synced "
             "under types/. Leaves rows for unknown maps (user-added, not from our sync) untouched.",
    )
    args = parser.parse_args()

    ddnet_root = map_sync.get_ddnet_root(args.ddnet_root)

    def cli_progress(payload):
        stream = sys.stderr if args.json else sys.stdout
        print(f"[{payload.get('stage','reg')}] {payload.get('message','')}", file=stream)

    if args.dry_run:
        # Best-effort preview: report what ensure_storage_cfg WOULD do and what maps would be inserted.
        cfg_path = Path(args.storage_cfg) if args.storage_cfg else (ddnet_root / STORAGE_CFG_FILENAME)
        existing = cfg_path.read_text(encoding="utf-8") if cfg_path.exists() else ""
        target_lines = _build_storage_cfg_target_lines(ddnet_root)
        if not cfg_path.exists():
            cfg_action = "created"
        elif not _missing_target_lines(existing, target_lines):
            cfg_action = "no-op"
        else:
            cfg_action = "appended"
        manifest = _collect_maps_from_types(ddnet_root / "types")
        summary = {
            "storage_cfg": {"action": cfg_action, "path": str(cfg_path), "target_lines": target_lines},
            "record_maps": {"would_consider": len(manifest)},
            "dry_run": True,
        }
    else:
        storage_cfg_path = Path(args.storage_cfg) if args.storage_cfg else None
        summary = register_with_server(ddnet_root, callback=cli_progress, storage_cfg_path=storage_cfg_path)
        if args.repair_server_column:
            summary["repair_server_column"] = repair_server_column(ddnet_root, callback=cli_progress)

    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        for k, v in summary.items():
            print(f"{k}: {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
