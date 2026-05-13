#!/usr/bin/env python3
"""Phase 1 verification matrix — real sync against live %APPDATA%\\DDNet\\.

Produces evidence files under:
  .planning/phases/01-harden-and-verify-sync-engine/evidence/

Exits 0 on full success. On any assertion failure, writes
VERIFICATION-ERROR.txt and exits 1.
"""

from __future__ import annotations

import hashlib
import http.server
import io
import json
import multiprocessing
import os
import shutil
import socketserver
import subprocess
import sys
import tempfile
import threading
import time
import traceback
import urllib.error
import urllib.request
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parent.parent
EVIDENCE_DIR = REPO_ROOT / ".planning" / "phases" / "01-harden-and-verify-sync-engine" / "evidence"

sys.path.insert(0, str(REPO_ROOT / "tools"))
import map_sync  # noqa: E402


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
    out: list[dict] = []
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
        "types_count": sum(1 for _ in (ddnet_root / "types").rglob("*.map")) if (ddnet_root / "types").exists() else 0,
    }


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


# ----------------------------------------------------------------------------
# Step 2 — Precheck abort
# ----------------------------------------------------------------------------
def step_precheck_abort() -> None:
    print("[verify] Step 2: precheck abort test (subprocess, isolated)", file=sys.stderr)
    # Run an isolated child that monkey-patches URL reachability
    script = """
import sys, json, io, tempfile, urllib.error, urllib.request
from pathlib import Path
from unittest import mock
sys.path.insert(0, r"{tools_dir}")
import map_sync

with tempfile.TemporaryDirectory() as root:
    types_root = Path(root)
    (types_root / 'testingmaps').mkdir(parents=True)
    sentinel = types_root / 'testingmaps' / 'existing.map'
    sentinel.write_bytes(b'sentinel-intact')

    def fake_request_json(url):
        return {{'Alpha': {{'urls': ['https://x.test/Alpha.map']}}}}

    def fake_urlopen(request, timeout=0):
        method = getattr(request, 'method', None) or request.get_method()
        if method == 'HEAD':
            raise urllib.error.HTTPError(request.full_url, 404, 'Not Found', hdrs=None, fp=io.BytesIO(b''))
        raise AssertionError('unexpected GET')

    with mock.patch.object(map_sync, 'request_json', side_effect=fake_request_json), \\
         mock.patch.object(urllib.request, 'urlopen', side_effect=fake_urlopen):
        try:
            map_sync.sync_testing_maps(types_root, {{'version':1,'official':{{'files':{{}}}},'testing':{{'files':{{}}}} }}, dry_run=False)
        except RuntimeError as e:
            if 'unreachable' not in str(e).lower():
                print('ERROR: wrong exception message:', e, file=sys.stderr); sys.exit(2)
            # assert sentinel intact
            if sentinel.read_bytes() != b'sentinel-intact':
                print('ERROR: sentinel modified', file=sys.stderr); sys.exit(3)
            if (types_root / '.ddnetcontrol-testingmaps.tmp').exists():
                print('ERROR: temp dir created', file=sys.stderr); sys.exit(4)
            # ok
            print(json.dumps({{'passed': True, 'error_message': str(e), 'sentinel_intact': True, 'temp_dir_absent': True}}))
            sys.exit(0)
        else:
            print('ERROR: no exception raised', file=sys.stderr); sys.exit(5)
""".format(tools_dir=str(REPO_ROOT / "tools").replace("\\", "\\\\"))

    proc = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True, text=True,
    )
    report = {
        "passed": proc.returncode == 0,
        "child_exit": proc.returncode,
        "stdout": proc.stdout.strip(),
        "stderr_excerpt": proc.stderr[-500:],
    }
    write_json(EVIDENCE_DIR / "precheck-abort-report.json", report)
    if proc.returncode != 0:
        fail(f"precheck-abort child exited {proc.returncode}: {proc.stderr}")


# ----------------------------------------------------------------------------
# Step 3 + 4 — Live full sync + idempotent rerun
# ----------------------------------------------------------------------------
def step_live_sync(label: str, evidence_name: str) -> dict:
    print(f"[verify] Step: live sync ({label})  —  expect ~20-60 min for a first run", file=sys.stderr)
    started = time.time()
    proc = subprocess.run(
        [sys.executable, str(REPO_ROOT / "tools" / "map_sync.py"),
         "--mode", "official", "--json"],
        capture_output=True, text=True,
    )
    elapsed = time.time() - started
    # Persist stderr log for diagnosis
    write_text(EVIDENCE_DIR / f"{evidence_name}.stderr.log",
               f"elapsed_s={elapsed:.1f}\nexit={proc.returncode}\n\n{proc.stderr}")
    if proc.returncode != 0:
        fail(f"Live sync ({label}) exit={proc.returncode}: {proc.stderr[-2000:]}")
    try:
        summary = json.loads(proc.stdout)
    except json.JSONDecodeError as e:
        fail(f"Live sync ({label}) did not emit parseable JSON on stdout. Got: {proc.stdout[:500]}...", e)
    summary["_elapsed_s"] = round(elapsed, 1)
    write_json(EVIDENCE_DIR / f"{evidence_name}.json", summary)
    return summary


# ----------------------------------------------------------------------------
# Step 5 — Interrupt-and-resume (temp tree, synthetic upstream)
# ----------------------------------------------------------------------------
class _SyntheticHandler(http.server.BaseHTTPRequestHandler):
    _tree_payload: dict = {}
    _blobs: dict[str, bytes] = {}

    def do_GET(self):  # noqa: N802
        path = self.path.split("?")[0].lstrip("/")
        if path == "tree":
            body = json.dumps(self._tree_payload).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if path in self._blobs:
            body = self._blobs[path]
            # Slow down each blob so we can interrupt mid-run reliably
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            # Trickle in 4 KB chunks with a short sleep — interruptible
            pos = 0
            chunk_sz = 4096
            while pos < len(body):
                try:
                    self.wfile.write(body[pos:pos + chunk_sz])
                    pos += chunk_sz
                    time.sleep(0.05)
                except (BrokenPipeError, ConnectionResetError):
                    return
            return
        self.send_error(404)

    def log_message(self, *_args):
        pass  # silence


def _run_sync_child(types_root: str, tree_url: str, raw_base: str, result_queue) -> None:
    # Runs in a child process: mutate module globals, call sync.
    import importlib
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import map_sync as ms
    ms.OFFICIAL_TREE_URL = tree_url
    ms.OFFICIAL_RAW_BASE = raw_base
    state = {"version": 1, "official": {"files": {}}, "testing": {"files": {}}}
    try:
        ms.sync_official_types(Path(types_root), state, dry_run=False)
        result_queue.put(("done", None))
    except BaseException as e:  # noqa: BLE001
        result_queue.put(("error", f"{type(e).__name__}: {e}"))


def step_interrupt_resume() -> None:
    print("[verify] Step 5: interrupt+resume (temp tree, synthetic upstream)", file=sys.stderr)
    with tempfile.TemporaryDirectory() as tmp:
        temp_root = Path(tmp)
        types_root = temp_root / "types"
        types_root.mkdir()

        # Build 20 synthetic blobs of 256 KB each
        blob_count = 20
        blob_size = 256 * 1024
        blobs: dict[str, bytes] = {}
        tree_items = []
        for i in range(blob_count):
            rel = f"synthetic/blob_{i:02d}.map"
            path = f"types/{rel}"
            # Deterministic pseudo-random content
            content = (bytes([i]) * blob_size)
            blobs[path] = content
            tree_items.append({
                "path": path,
                "type": "blob",
                "sha": hashlib.sha1(content).hexdigest(),  # any 40-char hex
                "size": blob_size,
            })
        tree_payload = {"sha": "0" * 40, "tree": tree_items}

        _SyntheticHandler._tree_payload = tree_payload
        _SyntheticHandler._blobs = blobs

        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _SyntheticHandler)
        port = server.server_port
        threading.Thread(target=server.serve_forever, daemon=True).start()
        tree_url = f"http://127.0.0.1:{port}/tree"
        raw_base = f"http://127.0.0.1:{port}/"

        try:
            # First attempt: start child, kill mid-run
            q = multiprocessing.Queue()
            ctx = multiprocessing.get_context("spawn")
            p = ctx.Process(target=_run_sync_child, args=(str(types_root), tree_url, raw_base, q))
            p.start()
            # Wait until ~5 .map files exist, then terminate
            deadline = time.time() + 120
            while time.time() < deadline:
                count = sum(1 for _ in types_root.rglob("*.map"))
                if count >= 5:
                    break
                if not p.is_alive():
                    break
                time.sleep(0.2)
            if p.is_alive():
                p.terminate()
                p.join(timeout=10)
                if p.is_alive():
                    p.kill()
                    p.join(timeout=5)

            # Post-kill check: orphans are expected when process is hard-killed
            # (OS bypasses BaseException cleanup). What matters is (a) no zero-byte
            # .map file is ever visible AND (b) next-run sweep clears them.
            partial_after_kill = list(types_root.rglob(".ddnetcontrol-download-*"))
            zero_byte = [x for x in types_root.rglob("*.map") if x.stat().st_size == 0]
            files_after_kill = sorted(str(x.relative_to(types_root)).replace("\\", "/")
                                       for x in types_root.rglob("*.map"))

            # Resume run — this should sweep any orphan temp files as its first step
            q2 = multiprocessing.Queue()
            p2 = ctx.Process(target=_run_sync_child, args=(str(types_root), tree_url, raw_base, q2))
            p2.start()
            p2.join(timeout=180)
            if p2.is_alive():
                p2.terminate()
                fail("interrupt+resume: resume child timed out")

            files_after_resume = sorted(str(x.relative_to(types_root)).replace("\\", "/")
                                         for x in types_root.rglob("*.map"))
            sizes_correct = all(x.stat().st_size == blob_size for x in types_root.rglob("*.map"))
            partial_after_resume = list(types_root.rglob(".ddnetcontrol-download-*"))

            report = (
                f"# Interrupt & Resume report\n\n"
                f"- blob_count: {blob_count}\n"
                f"- blob_size: {blob_size} bytes\n"
                f"- upstream: local synthetic HTTP server on port {port}\n"
                f"- types_root: {types_root}\n\n"
                f"## Post-kill state (process hard-terminated by orchestrator)\n\n"
                f"- .map files present: {len(files_after_kill)}\n"
                f"- partial (.ddnetcontrol-download-*) temp files: {len(partial_after_kill)}\n"
                f"  (expected to be >= 0 after hard kill — temp files are NOT visible as .map\n"
                f"   and the next run sweeps them; see post-resume state below.)\n"
                f"- zero-byte .map files: {len(zero_byte)}  (MUST be 0)\n\n"
                f"## Post-resume state\n\n"
                f"- .map files present: {len(files_after_resume)}\n"
                f"- partial (.ddnetcontrol-download-*) temp files: {len(partial_after_resume)}\n"
                f"- all expected sizes: {sizes_correct}\n"
                f"- files: {files_after_resume[:5]} ... {files_after_resume[-2:]}\n\n"
                f"## Assertions\n\n"
                f"- {'PASS' if not zero_byte else 'FAIL'}: no zero-byte .map files visible after kill\n"
                f"- {'PASS' if not partial_after_resume else 'FAIL'}: next-run sweep cleared all download orphans\n"
                f"- {'PASS' if len(files_after_resume) == blob_count else 'FAIL'}: all {blob_count} .map files present after resume\n"
                f"- {'PASS' if sizes_correct else 'FAIL'}: all .map files have correct size after resume\n"
            )
            write_text(EVIDENCE_DIR / "interrupt-resume-report.md", report)

            if zero_byte:
                fail(f"interrupt+resume: {len(zero_byte)} zero-byte .map file(s) visible after kill: {zero_byte}")
            if partial_after_resume:
                fail(f"interrupt+resume: next-run sweep failed to clear orphans: {partial_after_resume}")
            if len(files_after_resume) != blob_count:
                fail(f"interrupt+resume: expected {blob_count} files after resume, got {len(files_after_resume)}")
            if not sizes_correct:
                fail("interrupt+resume: at least one .map file has wrong size after resume")
        finally:
            server.shutdown()
            server.server_close()


# ----------------------------------------------------------------------------
# Step 7 — state-file check
# ----------------------------------------------------------------------------
def step_state_snapshot(ddnet_root: Path) -> None:
    state_path = ddnet_root / "types" / ".ddnetcontrol-sync-state.json"
    if not state_path.exists():
        fail(f"state file missing: {state_path}")
    data = json.loads(state_path.read_text(encoding="utf-8"))
    official = data.get("official", {})
    files = official.get("files", {})
    files_count = official.get("files_count", -1)
    tree_sha = official.get("upstream_tree_sha")
    orphans = official.get("orphans", [])

    if len(files) < 2000:
        fail(f"state.official.files has only {len(files)} entries; expected >= 2000")
    if files_count != len(files):
        fail(f"files_count={files_count} != len(files)={len(files)}")
    if not (isinstance(tree_sha, str) and len(tree_sha) == 40):
        fail(f"upstream_tree_sha invalid: {tree_sha!r}")

    keys = sorted(files.keys())
    sample_keys = keys[:3]
    sample = {k: files[k] for k in sample_keys}
    for k, v in sample.items():
        for field in ("sha", "size", "source_path", "download_url"):
            if field not in v:
                fail(f"state entry {k!r} missing field {field}")
        if not v["source_path"].startswith("types/"):
            fail(f"state entry {k!r} source_path doesn't start with types/: {v['source_path']}")

    snapshot = {
        "captured_at": utc_iso(),
        "state_path": str(state_path),
        "files_count": files_count,
        "files_len": len(files),
        "upstream_tree_sha": tree_sha,
        "synced_at": official.get("synced_at"),
        "orphans": orphans,
        "orphans_count": len(orphans),
        "first_10_keys": keys[:10],
        "last_10_keys": keys[-10:],
        "sample_entry": {sample_keys[0]: sample[sample_keys[0]]} if sample_keys else {},
    }
    write_json(EVIDENCE_DIR / "state-snapshot.json", snapshot)


# ----------------------------------------------------------------------------
# Step 6 — write-boundary diff
# ----------------------------------------------------------------------------
def step_write_boundary_diff(pre: dict, post: dict) -> None:
    lines: list[str] = ["# Write-boundary diff\n"]
    verdicts: list[str] = []

    # DB hashes
    for db_name in ("ddnet-server.sqlite", "ddnet-cache.sqlite3"):
        a = pre["db_hashes"][db_name]
        b = post["db_hashes"][db_name]
        if a == b:
            line = f"PASS: {db_name} SHA256 unchanged ({a[:12] if a else 'absent'}...)"
        else:
            line = f"FAIL: {db_name} SHA256 CHANGED: {a} -> {b}"
        lines.append(line)
        verdicts.append(line)

    # maps/ diff
    maps_pre = {x["relpath"]: (x["size"], x["mtime_ns"]) for x in pre["maps"]}
    maps_post = {x["relpath"]: (x["size"], x["mtime_ns"]) for x in post["maps"]}
    added = sorted(set(maps_post) - set(maps_pre))
    removed = sorted(set(maps_pre) - set(maps_post))
    changed = sorted(k for k in set(maps_pre) & set(maps_post) if maps_pre[k] != maps_post[k])
    if not added and not removed and not changed:
        line = f"PASS: maps/ unchanged ({len(maps_pre)} files)"
    else:
        line = (f"FAIL: maps/ changed — added={len(added)} removed={len(removed)} "
                f"changed={len(changed)}")
        if added[:3]:
            line += f"\n  added samples: {added[:3]}"
        if removed[:3]:
            line += f"\n  removed samples: {removed[:3]}"
        if changed[:3]:
            line += f"\n  changed samples: {changed[:3]}"
    lines.append(line)
    verdicts.append(line)

    # downloadedmaps/ diff
    dlm_pre = {x["relpath"]: (x["size"], x["mtime_ns"]) for x in pre["downloadedmaps"]}
    dlm_post = {x["relpath"]: (x["size"], x["mtime_ns"]) for x in post["downloadedmaps"]}
    added = sorted(set(dlm_post) - set(dlm_pre))
    removed = sorted(set(dlm_pre) - set(dlm_post))
    changed = sorted(k for k in set(dlm_pre) & set(dlm_post) if dlm_pre[k] != dlm_post[k])
    if not added and not removed and not changed:
        line = f"PASS: downloadedmaps/ unchanged ({len(dlm_pre)} files)"
    else:
        line = (f"FAIL: downloadedmaps/ changed — added={len(added)} removed={len(removed)} "
                f"changed={len(changed)}")
    lines.append(line)
    verdicts.append(line)

    # types/ summary (expected to grow)
    pre_types = pre.get("types_count", 0)
    post_types = post.get("types_count", 0)
    lines.append(f"INFO: types/ file count pre={pre_types}, post={post_types} (delta={post_types - pre_types})")

    body = "\n".join(lines) + "\n"
    write_text(EVIDENCE_DIR / "write-boundary-diff.txt", body)

    fails = [v for v in verdicts if v.startswith("FAIL")]
    if fails:
        fail("Write-boundary audit FAILED:\n" + "\n".join(fails))


# ----------------------------------------------------------------------------
# Driver
# ----------------------------------------------------------------------------
def main() -> int:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    # Wipe any prior error marker
    err_marker = EVIDENCE_DIR / "VERIFICATION-ERROR.txt"
    if err_marker.exists():
        err_marker.unlink()

    ddnet_root = map_sync.get_ddnet_root(None)
    print(f"[verify] DDNet root: {ddnet_root}", file=sys.stderr)

    # Step 1: pre-snapshot
    print("[verify] Step 1: pre-snapshot", file=sys.stderr)
    pre = snapshot_state(ddnet_root)
    write_json(EVIDENCE_DIR / "pre-snapshot.json", pre)

    # Step 2: precheck abort (sandboxed subprocess)
    step_precheck_abort()

    # Step 5: interrupt+resume against temp tree — do this BEFORE live sync
    #   so the live sync isn't racing with multiprocessing fork hacks
    step_interrupt_resume()

    # Step 3: live full sync
    full = step_live_sync("full", "full-sync-report")
    if not full.get("success"):
        fail(f"full sync did not report success: {full}")
    off = full.get("official", {})
    rfc = off.get("remote_file_count", 0)
    created = off.get("created", 0)
    updated = off.get("updated", 0)
    skipped = off.get("skipped", 0)
    if rfc != created + updated + skipped:
        fail(f"full sync: remote_file_count({rfc}) != created({created})+updated({updated})+skipped({skipped})")
    if rfc < 2000:
        fail(f"full sync: remote_file_count={rfc} < 2000")
    # downloaded_bytes may be 0 if a prior partial sync already grabbed them; treat as warning
    if off.get("downloaded_bytes", 0) == 0:
        print("[verify] WARN: full sync downloaded_bytes=0 (prior sync already populated types/)",
              file=sys.stderr)

    # Step 4: idempotent rerun
    rerun = step_live_sync("rerun", "rerun-idempotent-report")
    off2 = rerun.get("official", {})
    if off2.get("created", 0) != 0 or off2.get("updated", 0) != 0 or off2.get("downloaded_bytes", 0) != 0:
        fail(f"idempotent rerun: expected 0 new work, got {off2}")
    if off2.get("skipped", 0) != off2.get("remote_file_count", -1):
        fail(f"idempotent rerun: skipped={off2.get('skipped')} != remote_file_count={off2.get('remote_file_count')}")

    # Step 7: state snapshot
    step_state_snapshot(ddnet_root)

    # Step 6: post-snapshot + boundary diff
    print("[verify] Step 6: post-snapshot + write-boundary diff", file=sys.stderr)
    post = snapshot_state(ddnet_root)
    write_json(EVIDENCE_DIR / "post-snapshot.json", post)
    step_write_boundary_diff(pre, post)

    print("[verify] ALL STEPS PASSED", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
