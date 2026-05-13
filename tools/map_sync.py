#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Callable

USER_AGENT = "ddnetcontrol-map-sync/1.0"
OFFICIAL_TREE_URL = "https://api.github.com/repos/ddnet/ddnet-maps/git/trees/master?recursive=1"
OFFICIAL_RAW_BASE = "https://raw.githubusercontent.com/ddnet/ddnet-maps/master/"
TESTING_JSON_URL = "https://twdata.pati.ga/maplists/ddnet-testing.json"

STATE_FILENAME = ".ddnetcontrol-sync-state.json"
LOCK_FILENAME = ".ddnetcontrol-sync.lock"

ProgressCallback = Callable[[dict[str, Any]], None]


def get_ddnet_root(custom_root: str | None = None) -> Path:
    if custom_root:
        return Path(custom_root)

    appdata = os.environ.get("APPDATA")
    if not appdata:
        raise RuntimeError("APPDATA is not set")
    return Path(appdata) / "DDNet"


def emit_progress(callback: ProgressCallback | None, **payload: Any) -> None:
    if callback is None:
        return
    callback(payload)


def request_json(url: str) -> Any:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)


def stream_download(url: str, destination: Path) -> int:
    destination.parent.mkdir(parents=True, exist_ok=True)

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "*/*",
        },
    )

    temp_fd, temp_name = tempfile.mkstemp(
        prefix=".ddnetcontrol-download-",
        dir=str(destination.parent),
    )
    os.close(temp_fd)
    temp_path = Path(temp_name)

    try:
        with urllib.request.urlopen(request, timeout=120) as response, temp_path.open("wb") as file_handle:
            shutil.copyfileobj(response, file_handle)
        size = temp_path.stat().st_size
        os.replace(temp_path, destination)
        return size
    except BaseException:
        # Broader than Exception so KeyboardInterrupt / SystemExit also clean up.
        if temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                pass
        raise


def load_state(state_path: Path) -> dict[str, Any]:
    if not state_path.exists():
        return {
            "version": 1,
            "official": {"files": {}},
            "testing": {"files": {}},
        }

    try:
        return json.loads(state_path.read_text(encoding="utf-8"))
    except Exception:
        return {
            "version": 1,
            "official": {"files": {}},
            "testing": {"files": {}},
        }


def save_state(state_path: Path, state: dict[str, Any]) -> None:
    state_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = state_path.with_suffix(state_path.suffix + ".tmp")
    temp_path.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(temp_path, state_path)


def acquire_lock(lock_path: Path) -> None:
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        raise RuntimeError(f"Sync already running: {lock_path}") from exc

    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(json.dumps({"pid": os.getpid(), "started_at": time.time()}, indent=2))


def release_lock(lock_path: Path) -> None:
    if lock_path.exists():
        lock_path.unlink()


def collect_official_entries(tree_payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    entries: dict[str, dict[str, Any]] = {}
    for entry in tree_payload.get("tree", []):
        path = entry.get("path", "")
        if entry.get("type") != "blob":
            continue
        if not path.startswith("types/"):
            continue

        relative_path = path[len("types/") :]
        entries[relative_path] = {
            "sha": entry["sha"],
            "size": entry.get("size", 0),
            "source_path": path,
            "download_url": OFFICIAL_RAW_BASE + urllib.parse.quote(path, safe="/"),
        }
    return entries


def sync_official_types(
    types_root: Path,
    state: dict[str, Any],
    dry_run: bool = False,
    callback: ProgressCallback | None = None,
) -> dict[str, Any]:
    # Sweep any orphan download temp files from a prior hard-killed run.
    # stream_download cleans on exception, but OS-level kill bypasses that.
    if not dry_run and types_root.exists():
        orphan_count = 0
        for orphan in types_root.rglob(".ddnetcontrol-download-*"):
            try:
                orphan.unlink()
                orphan_count += 1
            except OSError:
                pass
        if orphan_count:
            emit_progress(
                callback, stage="official",
                message=f"Swept {orphan_count} leftover download orphan(s) from prior run",
            )

    emit_progress(callback, stage="official", message="Fetching upstream official types tree")
    tree_payload = request_json(OFFICIAL_TREE_URL)
    entries = collect_official_entries(tree_payload)
    previous_files = state.get("official", {}).get("files", {})

    summary = {
        "remote_file_count": len(entries),
        "remote_total_bytes": sum(item["size"] for item in entries.values()),
        "created": 0,
        "updated": 0,
        "skipped": 0,
        "orphaned_local_files": 0,
        "downloaded_bytes": 0,
        "dry_run": dry_run,
    }

    orphaned = sorted(set(previous_files) - set(entries))
    summary["orphaned_local_files"] = len(orphaned)

    next_manifest: dict[str, Any] = {}
    processed = 0
    download_candidates = []

    for relative_path, metadata in sorted(entries.items()):
        target_path = types_root / relative_path
        previous = previous_files.get(relative_path)
        file_matches = (
            target_path.exists()
            and target_path.is_file()
            and target_path.stat().st_size == metadata["size"]
        )
        if previous and previous.get("sha") == metadata["sha"] and file_matches:
            summary["skipped"] += 1
            next_manifest[relative_path] = metadata
            continue

        download_candidates.append((relative_path, metadata, target_path, previous is not None and target_path.exists()))

    emit_progress(
        callback,
        stage="official",
        message="Prepared official sync plan",
        counts={
            "remote_files": summary["remote_file_count"],
            "created": sum(1 for _, _, _, had_previous in download_candidates if not had_previous),
            "updated": sum(1 for _, _, _, had_previous in download_candidates if had_previous),
            "skipped": summary["skipped"],
            "orphans": summary["orphaned_local_files"],
        },
    )

    for relative_path, metadata, target_path, had_previous in download_candidates:
        processed += 1
        if dry_run:
            if had_previous:
                summary["updated"] += 1
            else:
                summary["created"] += 1
            next_manifest[relative_path] = metadata
            continue

        emit_progress(
            callback,
            stage="official",
            message=f"Downloading {relative_path}",
            progress={"current": processed, "total": len(download_candidates)},
        )
        bytes_written = stream_download(metadata["download_url"], target_path)
        summary["downloaded_bytes"] += bytes_written
        if had_previous:
            summary["updated"] += 1
        else:
            summary["created"] += 1
        next_manifest[relative_path] = metadata

    state["official"] = {
        "synced_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "upstream_tree_sha": tree_payload.get("sha"),
        "files": next_manifest if not dry_run else previous_files | next_manifest,
        "files_count": len(next_manifest if not dry_run else previous_files | next_manifest),
        "orphans": orphaned,
    }
    return summary


def testing_source_hash(testing_payload: dict[str, Any]) -> str:
    normalized = json.dumps(testing_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(normalized).hexdigest()


def resolve_testing_filename(name: str, url: str, taken: set[str]) -> str:
    parsed = urllib.parse.urlparse(url)
    basename = Path(urllib.parse.unquote(parsed.path)).name
    filename = basename or f"{name}.map"
    if not filename.lower().endswith(".map"):
        filename = f"{filename}.map"

    candidate = filename
    counter = 1
    while candidate in taken:
        stem = Path(filename).stem
        suffix = Path(filename).suffix
        candidate = f"{stem} ({counter}){suffix}"
        counter += 1
    taken.add(candidate)
    return candidate


def check_url_reachable(url: str, timeout: float = 5.0) -> tuple[bool, str]:
    """Return (reachable, reason). Tries HEAD, falls back to ranged GET on 405."""
    try:
        request = urllib.request.Request(
            url,
            headers={"User-Agent": USER_AGENT, "Accept": "*/*"},
            method="HEAD",
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status = getattr(response, "status", 200)
            if 200 <= status < 400:
                return True, f"HEAD {status}"
            return False, f"HEAD {status}"
    except urllib.error.HTTPError as exc:
        if exc.code == 405:
            # Fallback: ranged GET for servers that reject HEAD
            try:
                request = urllib.request.Request(
                    url,
                    headers={
                        "User-Agent": USER_AGENT,
                        "Accept": "*/*",
                        "Range": "bytes=0-0",
                    },
                )
                with urllib.request.urlopen(request, timeout=timeout) as response:
                    status = getattr(response, "status", 200)
                    if 200 <= status < 400:
                        return True, f"GET (ranged) {status}"
                    return False, f"GET (ranged) {status}"
            except urllib.error.HTTPError as inner:
                return False, f"GET (ranged) HTTPError {inner.code}"
            except Exception as inner:
                return False, f"GET (ranged) {type(inner).__name__}: {inner}"
        return False, f"HEAD HTTPError {exc.code}"
    except urllib.error.URLError as exc:
        return False, f"URLError: {exc.reason}"
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"


def sync_testing_maps(
    types_root: Path,
    state: dict[str, Any],
    dry_run: bool = False,
    callback: ProgressCallback | None = None,
) -> dict[str, Any]:
    testing_root = types_root / "testingmaps"
    emit_progress(callback, stage="testing", message="Fetching testing map list")
    testing_payload = request_json(TESTING_JSON_URL)

    entries = []
    taken: set[str] = set()
    for name, metadata in sorted(testing_payload.items()):
        urls = metadata.get("urls") or []
        if not urls:
            continue
        url = urls[0]
        filename = resolve_testing_filename(name, url, taken)
        entries.append({"name": name, "filename": filename, "url": url})

    # TEST-03: pre-validate every URL BEFORE any destructive local action.
    # On any failure, abort with a RuntimeError — testing_root is untouched.
    emit_progress(
        callback,
        stage="testing",
        message=f"Pre-validating {len(entries)} testing URL(s)",
    )
    unreachable: list[tuple[str, str]] = []
    for entry in entries:
        ok, reason = check_url_reachable(entry["url"])
        if not ok:
            unreachable.append((entry["filename"], reason))
    if unreachable:
        emit_progress(
            callback,
            stage="testing",
            message=f"Aborting: {len(unreachable)} testing URL(s) unreachable",
            counts={"unreachable": len(unreachable)},
        )
        preview = ", ".join(f"{n} ({r})" for n, r in unreachable[:3])
        suffix = "" if len(unreachable) <= 3 else f" (+{len(unreachable) - 3} more)"
        raise RuntimeError(
            f"Testing sync aborted — {len(unreachable)} URL(s) unreachable: {preview}{suffix}"
        )
    emit_progress(
        callback,
        stage="testing",
        message=f"Pre-validated {len(entries)} URL(s)",
    )

    summary = {
        "remote_file_count": len(entries),
        "replaced": len(entries),
        "deleted_existing": 0,
        "downloaded_bytes": 0,
        "dry_run": dry_run,
    }

    if dry_run:
        existing_maps = [path for path in testing_root.glob("*.map")] if testing_root.exists() else []
        summary["deleted_existing"] = len(existing_maps)
        state["testing"] = {
            "synced_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "source_hash": testing_source_hash(testing_payload),
            "files": {entry["filename"]: {"url": entry["url"]} for entry in entries},
        }
        return summary

    temp_root = types_root / ".ddnetcontrol-testingmaps.tmp"
    if temp_root.exists():
        shutil.rmtree(temp_root)
    temp_root.mkdir(parents=True, exist_ok=True)

    try:
        for index, entry in enumerate(entries, start=1):
            destination = temp_root / entry["filename"]
            emit_progress(
                callback,
                stage="testing",
                message=f"Downloading {entry['filename']}",
                progress={"current": index, "total": len(entries)},
            )
            summary["downloaded_bytes"] += stream_download(entry["url"], destination)

        testing_root.mkdir(parents=True, exist_ok=True)
        existing_maps = list(testing_root.glob("*.map"))
        for existing in existing_maps:
            existing.unlink()
        summary["deleted_existing"] = len(existing_maps)

        for temp_file in temp_root.iterdir():
            os.replace(temp_file, testing_root / temp_file.name)
    finally:
        if temp_root.exists():
            shutil.rmtree(temp_root)

    state["testing"] = {
        "synced_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "source_hash": testing_source_hash(testing_payload),
        "files": {entry["filename"]: {"url": entry["url"]} for entry in entries},
    }
    return summary


def sync_ddnet_maps(
    mode: str = "all",
    ddnet_root: str | None = None,
    dry_run: bool = False,
    callback: ProgressCallback | None = None,
    register_with_server: bool = False,
) -> dict[str, Any]:
    root = get_ddnet_root(ddnet_root)
    types_root = root / "types"
    types_root.mkdir(parents=True, exist_ok=True)

    state_path = types_root / STATE_FILENAME
    lock_path = types_root / LOCK_FILENAME
    state = load_state(state_path)

    summary: dict[str, Any] = {
        "mode": mode,
        "ddnet_root": str(root),
        "types_root": str(types_root),
        "state_file": str(state_path),
        "lock_file": str(lock_path),
        "dry_run": dry_run,
        "register_with_server": register_with_server,
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    acquire_lock(lock_path)
    try:
        if mode in ("official", "all"):
            summary["official"] = sync_official_types(
                types_root=types_root,
                state=state,
                dry_run=dry_run,
                callback=callback,
            )

        if mode in ("testing", "all"):
            summary["testing"] = sync_testing_maps(
                types_root=types_root,
                state=state,
                dry_run=dry_run,
                callback=callback,
            )

        if not dry_run:
            save_state(state_path, state)

        # Phase 2: server visibility. Off by default to avoid surprising
        # the Phase 1 verification matrix that runs before this feature is
        # wired into callers (website / native CLI).
        if register_with_server and not dry_run:
            try:
                # Import lazily so tests of sync_* don't pull in sqlite3 stubbing.
                import server_register  # noqa: WPS433
            except ImportError:
                # Also handle the case where this module is on the path under a different name
                from tools import server_register  # type: ignore
            summary["server_register"] = server_register.register_with_server(root, callback=callback)

        summary["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        summary["success"] = True
        return summary
    finally:
        release_lock(lock_path)


def print_summary(summary: dict[str, Any]) -> None:
    print(f"Mode: {summary['mode']}")
    print(f"Types root: {summary['types_root']}")
    if "official" in summary:
        official = summary["official"]
        print(
            "Official types:"
            f" remote={official['remote_file_count']}"
            f" created={official['created']}"
            f" updated={official['updated']}"
            f" skipped={official['skipped']}"
            f" orphans={official['orphaned_local_files']}"
        )
    if "testing" in summary:
        testing = summary["testing"]
        print(
            "Testing maps:"
            f" remote={testing['remote_file_count']}"
            f" replaced={testing['replaced']}"
            f" deleted_existing={testing['deleted_existing']}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync official DDNet types maps and testing maps")
    parser.add_argument(
        "--mode",
        choices=["all", "official", "testing"],
        default="all",
        help="Which sync subset to run",
    )
    parser.add_argument(
        "--ddnet-root",
        help="Override DDNet root directory (defaults to %%APPDATA%%\\DDNet)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Calculate sync work without writing files",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the final summary as JSON to stdout (progress goes to stderr)",
    )
    parser.add_argument(
        "--register-with-server",
        action="store_true",
        help="After sync, install storage.cfg (if missing) and INSERT OR IGNORE new maps into ddnet-server.sqlite record_maps (Phase 2)",
    )
    args = parser.parse_args()

    def cli_progress(payload: dict[str, Any]) -> None:
        stage = payload.get("stage", "sync")
        message = payload.get("message", "")
        # When --json is active, keep stdout pristine for the JSON summary.
        stream = sys.stderr if args.json else sys.stdout
        print(f"[{stage}] {message}", file=stream)

    summary = sync_ddnet_maps(
        mode=args.mode,
        ddnet_root=args.ddnet_root,
        dry_run=args.dry_run,
        callback=cli_progress,
        register_with_server=args.register_with_server,
    )

    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        print_summary(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
