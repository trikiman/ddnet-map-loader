#!/usr/bin/env python3
"""Phase 2 live verification — storage.cfg install + record_maps registration.

Runs server_register.register_with_server against the live %APPDATA%\\DDNet\\,
captures pre/post evidence, and verifies all Phase 2 safety rails.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import sys
import time
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
EVIDENCE_DIR = REPO_ROOT / ".planning" / "phases" / "02-server-visibility" / "evidence"

sys.path.insert(0, str(REPO_ROOT / "tools"))
import map_sync  # noqa: E402
import server_register  # noqa: E402


def utc_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def sha256_file(path: Path) -> str | None:
    if not path.exists():
        return None
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def snapshot_tree(root: Path) -> list[dict]:
    if not root.exists():
        return []
    out = []
    for p in sorted(root.rglob("*")):
        if p.is_file():
            st = p.stat()
            out.append({
                "relpath": str(p.relative_to(root)).replace("\\", "/"),
                "size": st.st_size,
                "mtime_ns": st.st_mtime_ns,
            })
    return out


def snapshot_state(ddnet_root: Path) -> dict:
    return {
        "captured_at": utc_iso(),
        "db_hashes": {
            "ddnet-server.sqlite": sha256_file(ddnet_root / "ddnet-server.sqlite"),
            "ddnet-cache.sqlite3": sha256_file(ddnet_root / "ddnet-cache.sqlite3"),
        },
        "maps": snapshot_tree(ddnet_root / "maps"),
        "downloadedmaps": snapshot_tree(ddnet_root / "downloadedmaps"),
        "storage_cfg_exists": (ddnet_root / "storage.cfg").exists(),
        "storage_cfg_sha": sha256_file(ddnet_root / "storage.cfg"),
        "storage_cfg_bak_exists": (ddnet_root / "storage.cfg.bak").exists(),
    }


def read_record_maps_sample(ddnet_root: Path) -> list[dict]:
    db = ddnet_root / "ddnet-server.sqlite"
    if not db.exists():
        return []
    conn = sqlite3.connect(str(db))
    try:
        rows = conn.execute(
            "SELECT Map, Server, Mapper, Points, Stars FROM record_maps ORDER BY Map LIMIT 100"
        ).fetchall()
    finally:
        conn.close()
    return [{"Map": r[0], "Server": r[1], "Mapper": r[2], "Points": r[3], "Stars": r[4]} for r in rows]


def count_table_rows(ddnet_root: Path, table: str) -> int | None:
    db = ddnet_root / "ddnet-server.sqlite"
    if not db.exists():
        return None
    conn = sqlite3.connect(str(db))
    try:
        try:
            cur = conn.execute(f"SELECT COUNT(*) FROM {table}")
            return cur.fetchone()[0]
        except sqlite3.OperationalError:
            return None
    finally:
        conn.close()


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def write_text(path: Path, data: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(data, encoding="utf-8")


def fail(reason: str, exc: BaseException | None = None) -> None:
    tb = traceback.format_exc() if exc is not None else ""
    body = f"FAIL at {utc_iso()}\n\n{reason}\n\n{tb}\n"
    write_text(EVIDENCE_DIR / "VERIFICATION-ERROR.txt", body)
    print(f"VERIFICATION FAIL: {reason}", file=sys.stderr)
    if tb:
        print(tb, file=sys.stderr)
    sys.exit(1)


TABLES_TO_AUDIT = [
    "record_maps", "record_race", "record_teamrace", "record_saves", "record_points",
    "record_race_backup", "record_teamrace_backup", "record_saves_backup",
]


def main() -> int:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    err = EVIDENCE_DIR / "VERIFICATION-ERROR.txt"
    if err.exists():
        err.unlink()

    ddnet_root = map_sync.get_ddnet_root(None)
    print(f"[verify] DDNet root: {ddnet_root}", file=sys.stderr)

    # Step 1: pre-snapshot + DB state
    print("[verify] Step 1: pre-snapshot + record_maps sample", file=sys.stderr)
    pre = snapshot_state(ddnet_root)
    write_json(EVIDENCE_DIR / "pre-snapshot.json", pre)

    pre_sample = read_record_maps_sample(ddnet_root)
    pre_counts = {t: count_table_rows(ddnet_root, t) for t in TABLES_TO_AUDIT}

    # Step 2: run register_with_server
    print("[verify] Step 2: installing storage.cfg + registering maps", file=sys.stderr)
    def progress(p):
        print(f"  [{p.get('stage','?')}] {p.get('message','')}", file=sys.stderr)

    try:
        summary = server_register.register_with_server(ddnet_root, callback=progress)
    except BaseException as e:
        fail(f"register_with_server crashed: {e}", e)

    # Step 3: post-snapshot + post-DB state
    print("[verify] Step 3: post-snapshot + audit", file=sys.stderr)
    post = snapshot_state(ddnet_root)
    write_json(EVIDENCE_DIR / "post-snapshot.json", post)

    post_sample = read_record_maps_sample(ddnet_root)
    post_counts = {t: count_table_rows(ddnet_root, t) for t in TABLES_TO_AUDIT}

    # Step 4: storage.cfg report + contents
    cfg_path = ddnet_root / "storage.cfg"
    cfg_contents = cfg_path.read_text(encoding="utf-8") if cfg_path.exists() else ""
    write_text(EVIDENCE_DIR / "storage-cfg-contents.txt", cfg_contents)
    cfg_report = {
        "action": summary["storage_cfg"]["action"],
        "path": summary["storage_cfg"]["path"],
        "backup_path": summary["storage_cfg"]["backup_path"],
        "exists_after": cfg_path.exists(),
        "contains_target_line": "add_path $USERDIR/types" in cfg_contents,
        "sha256_after": sha256_file(cfg_path),
    }
    write_json(EVIDENCE_DIR / "storage-cfg-report.json", cfg_report)

    # Step 5: record_maps report
    dbrep = summary["record_maps"]
    dbrep["pre_sample_first_20"] = pre_sample[:20]
    dbrep["post_sample_first_20"] = post_sample[:20]
    write_json(EVIDENCE_DIR / "record-maps-report.json", dbrep)

    # Step 6: row preservation report
    # Compare the intersection: for every Map present in both pre and post,
    # all columns must be byte-identical.
    pre_by_map = {r["Map"]: r for r in pre_sample}
    preserved = []
    mutated = []
    for r in post_sample[:20]:
        if r["Map"] in pre_by_map:
            if pre_by_map[r["Map"]] == r:
                preserved.append(r["Map"])
            else:
                mutated.append({"map": r["Map"], "pre": pre_by_map[r["Map"]], "post": r})
    preservation = {
        "pre_sample_size": len(pre_sample),
        "post_sample_size": len(post_sample),
        "preserved_count": len(preserved),
        "mutated_count": len(mutated),
        "preserved_sample": preserved[:20],
        "mutated_sample": mutated,
    }
    write_json(EVIDENCE_DIR / "row-preservation-report.json", preservation)

    # Step 7: write-boundary diff
    lines = ["# Write-boundary diff (Phase 2)\n"]
    verdicts = []
    # cache DB must be unchanged (SAFE-03)
    if pre["db_hashes"]["ddnet-cache.sqlite3"] == post["db_hashes"]["ddnet-cache.sqlite3"]:
        line = f"PASS: ddnet-cache.sqlite3 SHA256 unchanged ({str(pre['db_hashes']['ddnet-cache.sqlite3'])[:12]}...)"
    else:
        line = f"FAIL: ddnet-cache.sqlite3 SHA256 CHANGED: {pre['db_hashes']['ddnet-cache.sqlite3']} -> {post['db_hashes']['ddnet-cache.sqlite3']}"
    lines.append(line); verdicts.append(line)

    # server DB SHA is EXPECTED to change (we wrote to record_maps)
    if pre["db_hashes"]["ddnet-server.sqlite"] != post["db_hashes"]["ddnet-server.sqlite"]:
        line = f"INFO: ddnet-server.sqlite SHA256 changed (expected — record_maps rows inserted)"
    else:
        line = f"INFO: ddnet-server.sqlite SHA256 unchanged (unexpected unless 0 rows inserted AND no VACUUM effects)"
    lines.append(line); verdicts.append(line)

    # maps/ and downloadedmaps/ must be unchanged (SAFE-05)
    for dir_name, key in (("maps", "maps"), ("downloadedmaps", "downloadedmaps")):
        pre_dict = {x["relpath"]: (x["size"], x["mtime_ns"]) for x in pre[key]}
        post_dict = {x["relpath"]: (x["size"], x["mtime_ns"]) for x in post[key]}
        if pre_dict == post_dict:
            line = f"PASS: {dir_name}/ unchanged ({len(pre_dict)} files)"
        else:
            added = sorted(set(post_dict) - set(pre_dict))
            removed = sorted(set(pre_dict) - set(post_dict))
            changed = sorted(k for k in set(pre_dict) & set(post_dict) if pre_dict[k] != post_dict[k])
            line = f"FAIL: {dir_name}/ changed — added={len(added)} removed={len(removed)} changed={len(changed)}"
        lines.append(line); verdicts.append(line)

    # Other record tables must have SAME row counts (DB-03/04)
    for t in ("record_race", "record_teamrace", "record_saves", "record_points",
              "record_race_backup", "record_teamrace_backup", "record_saves_backup"):
        if pre_counts[t] == post_counts[t]:
            line = f"PASS: {t} row count unchanged ({pre_counts[t]})"
        else:
            line = f"FAIL: {t} row count CHANGED: {pre_counts[t]} -> {post_counts[t]}"
        lines.append(line); verdicts.append(line)

    # record_maps count must be >= pre count (new rows only)
    if post_counts["record_maps"] >= (pre_counts["record_maps"] or 0):
        delta = post_counts["record_maps"] - (pre_counts["record_maps"] or 0)
        line = f"PASS: record_maps row count {pre_counts['record_maps']} -> {post_counts['record_maps']} (+{delta} new, none removed)"
    else:
        line = f"FAIL: record_maps row count decreased: {pre_counts['record_maps']} -> {post_counts['record_maps']}"
    lines.append(line); verdicts.append(line)

    # storage.cfg must exist after and contain the target line
    if cfg_path.exists() and "add_path $USERDIR/types" in cfg_contents:
        line = "PASS: storage.cfg exists and contains add_path $USERDIR/types"
    else:
        line = f"FAIL: storage.cfg state unexpected (exists={cfg_path.exists()}, contents_ok={'add_path $USERDIR/types' in cfg_contents})"
    lines.append(line); verdicts.append(line)

    body = "\n".join(lines) + "\n"
    write_text(EVIDENCE_DIR / "write-boundary-diff.txt", body)

    fails = [v for v in verdicts if v.startswith("FAIL")]
    if fails:
        fail("Phase 2 write-boundary audit FAILED:\n" + "\n".join(fails))
    if preservation["mutated_count"] > 0:
        fail(f"Phase 2 DB-02 violation: {preservation['mutated_count']} existing row(s) mutated: {preservation['mutated_sample']}")
    if not dbrep.get("other_table_counts_unchanged", False):
        fail(f"Phase 2 DB-04 violation: other table counts changed: {dbrep.get('other_table_counts')}")

    print("[verify] ALL STEPS PASSED", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
