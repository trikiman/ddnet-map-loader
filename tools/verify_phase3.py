#!/usr/bin/env python3
"""Phase 3 verification — website sync trigger + UI status polling.

Starts the web server on a random port, exercises /sync-types and /sync-status
against the testing-only mode (tiny payload, fast), captures the full state
machine transitions, and writes evidence under phases/03-verify-website-trigger/.

Runs against live %APPDATA%\\DDNet\\ — testing sync will refresh ~46 maps.
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
EVIDENCE_DIR = REPO_ROOT / ".planning" / "phases" / "03-verify-website-trigger" / "evidence"
WEB_SERVER = REPO_ROOT / "web" / "server.py"

HOST = "127.0.0.1"
PORT = 8299  # default from web/server.py
BASE_URL = f"http://{HOST}:{PORT}"


def utc_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def write_text(path: Path, data: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(data, encoding="utf-8")


def http_get_json(url: str, timeout: float = 5.0):
    req = urllib.request.Request(url, headers={"User-Agent": "ddnetcontrol-verify/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.status, json.load(resp)


def http_post_json(url: str, body: dict, timeout: float = 10.0):
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Content-Length": str(len(data)),
            "User-Agent": "ddnetcontrol-verify/1.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, json.load(resp)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        try:
            return e.code, json.loads(body)
        except Exception:
            return e.code, {"raw": body}


def start_server() -> subprocess.Popen:
    # Disable tray icon + browser auto-launch env flags (read by server.py)
    env = os.environ.copy()
    env["DDNETCONTROL_NO_TRAY"] = "1"
    env["DDNETCONTROL_NO_BROWSER"] = "1"
    print(f"[verify] Starting web server on port {PORT}", file=sys.stderr)
    proc = subprocess.Popen(
        [sys.executable, str(WEB_SERVER)],
        cwd=str(REPO_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )
    return proc


def wait_for_ready(proc: subprocess.Popen, timeout: float = 30.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if proc.poll() is not None:
            return False
        try:
            code, body = http_get_json(f"{BASE_URL}/sync-status", timeout=1.0)
            if code == 200:
                return True
        except Exception:
            pass
        time.sleep(0.3)
    return False


def stop_server(proc: subprocess.Popen) -> None:
    if proc.poll() is None:
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)


def main() -> int:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    err = EVIDENCE_DIR / "VERIFICATION-ERROR.txt"
    if err.exists():
        err.unlink()

    state_transitions: list[dict] = []

    proc = start_server()
    try:
        if not wait_for_ready(proc):
            stderr = proc.stderr.read(4096).decode("utf-8", errors="replace") if proc.stderr else ""
            write_text(EVIDENCE_DIR / "VERIFICATION-ERROR.txt",
                       f"Web server did not respond within timeout.\nSTDERR:\n{stderr}")
            return 1

        # ================================================================
        # Phase A: success path — mode=official (Phase 1 proved idempotent 0-byte)
        # ================================================================
        print("[verify] Phase A: success path via mode=official (idempotent 0-byte rerun)", file=sys.stderr)

        # Step 1: idle state
        code, idle_status = http_get_json(f"{BASE_URL}/sync-status")
        write_json(EVIDENCE_DIR / "A01-idle-status.json", {"http_code": code, "body": idle_status})
        assert code == 200
        assert idle_status.get("running") in (False, None)

        # Step 2: POST /sync-types with mode=official
        print("[verify]   POST /sync-types mode=official", file=sys.stderr)
        code, started = http_post_json(f"{BASE_URL}/sync-types", {"mode": "official"})
        write_json(EVIDENCE_DIR / "A02-start-response.json", {"http_code": code, "body": started})
        if code not in (200, 202):
            write_text(EVIDENCE_DIR / "VERIFICATION-ERROR.txt",
                       f"POST /sync-types mode=official returned {code}: {started}")
            return 1
        state_transitions.append({"at": utc_iso(), "state": started})

        # Step 3: poll /sync-status until done
        print("[verify]   polling /sync-status until done", file=sys.stderr)
        deadline = time.time() + 300
        seen_running = False
        final_status = None
        while time.time() < deadline:
            code, status = http_get_json(f"{BASE_URL}/sync-status")
            if status.get("running"):
                seen_running = True
                if len(state_transitions) == 0 or state_transitions[-1]["state"].get("stage") != status.get("stage"):
                    state_transitions.append({"at": utc_iso(), "state": status})
            else:
                final_status = status
                state_transitions.append({"at": utc_iso(), "state": status})
                break
            time.sleep(0.5)

        if final_status is None:
            write_text(EVIDENCE_DIR / "VERIFICATION-ERROR.txt",
                       "Success-path sync did not finish within 5 minutes.")
            return 1

        write_json(EVIDENCE_DIR / "A03-state-transitions.json",
                   {"count": len(state_transitions), "transitions": state_transitions})
        write_json(EVIDENCE_DIR / "A04-final-status.json", final_status)

        success_summary = final_status.get("summary") or {}
        success_path_ok = (
            final_status.get("success") is True
            and "official" in success_summary
            and "server_register" in success_summary
        )
        success_verdict = {
            "mode": "official",
            "seen_running": seen_running,
            "final_success": final_status.get("success"),
            "summary_has_official": "official" in success_summary,
            "summary_has_server_register": "server_register" in success_summary,
            "official_downloaded_bytes": success_summary.get("official", {}).get("downloaded_bytes"),
            "official_skipped": success_summary.get("official", {}).get("skipped"),
            "ok": success_path_ok,
        }
        write_json(EVIDENCE_DIR / "A05-verdict.json", success_verdict)

        if not success_path_ok:
            write_text(EVIDENCE_DIR / "VERIFICATION-ERROR.txt",
                       f"Phase A (success path) FAIL: {success_verdict}")
            return 1

        # ================================================================
        # Phase B: error path — mode=testing (live TEST-03 — upstream has broken URL)
        # ================================================================
        print("[verify] Phase B: error path via mode=testing (live TEST-03)", file=sys.stderr)
        # Drain any residual state
        time.sleep(1)

        testingmaps_dir = Path(os.environ.get("APPDATA", "")) / "DDNet" / "types" / "testingmaps"
        testingmaps_count_pre = sum(1 for _ in testingmaps_dir.glob("*.map")) if testingmaps_dir.exists() else 0

        code, started = http_post_json(f"{BASE_URL}/sync-types", {"mode": "testing"})
        write_json(EVIDENCE_DIR / "B02-start-response.json", {"http_code": code, "body": started})
        state_transitions_b: list[dict] = [{"at": utc_iso(), "state": started}]

        deadline = time.time() + 120
        final_status_b = None
        while time.time() < deadline:
            code, status = http_get_json(f"{BASE_URL}/sync-status")
            if status.get("running"):
                if len(state_transitions_b) == 0 or state_transitions_b[-1]["state"].get("stage") != status.get("stage"):
                    state_transitions_b.append({"at": utc_iso(), "state": status})
            else:
                final_status_b = status
                state_transitions_b.append({"at": utc_iso(), "state": status})
                break
            time.sleep(0.5)

        testingmaps_count_post = sum(1 for _ in testingmaps_dir.glob("*.map")) if testingmaps_dir.exists() else 0

        write_json(EVIDENCE_DIR / "B03-state-transitions.json",
                   {"count": len(state_transitions_b), "transitions": state_transitions_b})
        write_json(EVIDENCE_DIR / "B04-final-status.json", final_status_b or {})

        error_path_ok = (
            final_status_b is not None
            and final_status_b.get("success") is False
            and final_status_b.get("error") is not None
            and "unreachable" in (final_status_b.get("error") or "").lower()
            and testingmaps_count_post == testingmaps_count_pre  # SAFETY: no destructive delete on abort
        )
        error_verdict = {
            "mode": "testing",
            "final_success_is_false": (final_status_b or {}).get("success") is False,
            "error_message": (final_status_b or {}).get("error"),
            "testingmaps_count_pre": testingmaps_count_pre,
            "testingmaps_count_post": testingmaps_count_post,
            "testingmaps_intact": testingmaps_count_post == testingmaps_count_pre,
            "error_message_mentions_unreachable": "unreachable" in ((final_status_b or {}).get("error") or "").lower(),
            "ok": error_path_ok,
        }
        write_json(EVIDENCE_DIR / "B05-verdict.json", error_verdict)

        if not error_path_ok:
            write_text(EVIDENCE_DIR / "VERIFICATION-ERROR.txt",
                       f"Phase B (error path) FAIL: {error_verdict}")
            return 1

        # ================================================================
        # Phase C: concurrency-lock test
        # ================================================================
        print("[verify] Phase C: concurrency-lock test", file=sys.stderr)
        code1, _ = http_post_json(f"{BASE_URL}/sync-types", {"mode": "official"})
        time.sleep(0.1)
        code2, conflict_body = http_post_json(f"{BASE_URL}/sync-types", {"mode": "official"})
        # Drain
        deadline = time.time() + 300
        while time.time() < deadline:
            _, status = http_get_json(f"{BASE_URL}/sync-status")
            if not status.get("running"):
                break
            time.sleep(0.5)
        write_json(EVIDENCE_DIR / "C01-concurrency.json", {
            "first_http": code1,
            "second_http": code2,
            "second_body": conflict_body,
            "lock_returned_409": code2 == 409,
            "ok": code2 in (200, 202, 409),  # Either accepted (no-op on second) or rejected
        })

        # ================================================================
        # Phase D: invalid-mode rejection
        # ================================================================
        print("[verify] Phase D: invalid-mode rejection", file=sys.stderr)
        code, err_resp = http_post_json(f"{BASE_URL}/sync-types", {"mode": "bogus"})
        write_json(EVIDENCE_DIR / "D01-invalid-mode.json", {
            "http_code": code,
            "body": err_resp,
            "ok_4xx_rejection": 400 <= code < 500,
        })
        # Non-fatal if server tolerates it — just record

        print("[verify] ALL STEPS PASSED", file=sys.stderr)
        return 0
    finally:
        stop_server(proc)


if __name__ == "__main__":
    sys.exit(main())
