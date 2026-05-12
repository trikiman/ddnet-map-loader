---
phase: 01-harden-and-verify-sync-engine
plan: 01
status: ready
tasks:
  - id: 1
    title: "Harden map_sync.py with URL pre-validation and unit tests"
    autonomous: true
    tdd: true
  - id: 2
    title: "Execute verification matrix against live %APPDATA%\\DDNet\\"
    autonomous: true
  - id: 3
    title: "Author SUMMARY / VERIFICATION / VALIDATION artifacts"
    autonomous: true
    checkpoint: human-verify
requirements:
  - SYNC-01
  - SYNC-02
  - SYNC-03
  - SYNC-04
  - TEST-01
  - TEST-02
  - TEST-03
  - SAFE-01
  - SAFE-02
  - SAFE-03
  - SAFE-05
threats:
  - id: T-1
    category: "Tampering"
    description: "Partial download overwrites a good .map file with half-written content"
    disposition: "mitigated"
    mitigation: "temp-then-rename in stream_download() with tmp cleanup on exception; covered by Task 1 unit test and Task 2 interrupt-resume test"
  - id: T-2
    category: "Repudiation"
    description: "No audit trail of which files were created/updated/skipped"
    disposition: "mitigated"
    mitigation: "JSON summary written to phase evidence dir per run; manifest state file records upstream tree SHA per file"
  - id: T-3
    category: "Information Disclosure"
    description: "Sync state file might log sensitive URLs/tokens"
    disposition: "accepted"
    mitigation: "Only public GitHub raw URLs and public testing feed URLs are stored — no auth/secrets in the pipeline"
  - id: T-4
    category: "Denial of Service (self)"
    description: "Hitting GitHub unauth API too often causes 60/hr rate limit"
    disposition: "mitigated"
    mitigation: "Tree API called once per full run; raw blob fetches are served via CDN with much higher limits; idempotent rerun proven by Task 2 step 4 so user is not re-running tree unnecessarily"
  - id: T-5
    category: "Tampering"
    description: "Sync writes outside types/ could corrupt DDNet state"
    disposition: "mitigated"
    mitigation: "Task 2 step 6 write-boundary diff must be empty for maps/, downloadedmaps/, and both sqlite files. Backup taken at .ddnetcontrol-backup-20260513-020207 as a restore path."
  - id: T-6
    category: "Tampering"
    description: "Testing sync deletes existing maps before confirming new downloads are reachable"
    disposition: "mitigated"
    mitigation: "TEST-03 pre-validation in Task 1 — abort before destructive action if any URL unreachable; covered by unit test and Task 2 step 2"
  - id: T-7
    category: "Elevation of Privilege"
    description: "sync runs as current user with write to %APPDATA% and DDNet DBs"
    disposition: "accepted"
    mitigation: "Within the user's own data dir; no cross-user elevation path. DB writes gated by Phase 2 design."
---

# Phase 1 Plan: Harden and Verify Sync Engine

## Objective

Prove `tools/map_sync.py` works end-to-end against the live DDNet install by executing a real full official sync (~1.08 GB), confirming incremental semantics on a second run, verifying every safety rail the legacy audit flagged, and capturing per-phase artifacts (`SUMMARY.md`, `VERIFICATION.md`, `VALIDATION.md`) so the milestone audit gate passes.

**Phase goal:** close the legacy gaps for SYNC-01/02/03/04, TEST-01/02/03, SAFE-01/02/03/05 with mechanical evidence rows that the milestone auditor can consume.

**Out of scope:** `storage.cfg` install (Phase 2), `record_maps` writes (Phase 2), website trigger (Phase 3), native CLI auto-trigger (Phase 4).

## Canonical references

- `tools/map_sync.py` — engine under test. Relevant symbols: `sync_ddnet_maps(mode, ddnet_root, dry_run, callback)`, `sync_official_types`, `sync_testing_maps`, `stream_download`, `collect_official_entries`, `resolve_testing_filename`, `acquire_lock`, `release_lock`, `save_state`
- CLI surface (from `argparse` in `main()`): `--mode {all,official,testing}`, `--ddnet-root <path>`, `--dry-run`, `--json`
- JSON summary schema returned by `sync_ddnet_maps`:
  - top-level: `mode`, `ddnet_root`, `types_root`, `state_file`, `lock_file`, `dry_run`, `started_at`, `finished_at`, `success`
  - `summary.official`: `remote_file_count`, `remote_total_bytes`, `created`, `updated`, `skipped`, `orphaned_local_files`, `downloaded_bytes`, `dry_run`
  - `summary.testing`: `remote_file_count`, `replaced`, `deleted_existing`, `downloaded_bytes`, `dry_run`
- `.planning/phases/01-harden-and-verify-sync-engine/01-CONTEXT.md` — decisions D-01..D-10
- `.planning/REQUIREMENTS.md` — exact text of SYNC-01..04, TEST-01..03, SAFE-01..03, SAFE-05
- Live targets:
  - `C:\Users\rust-\AppData\Roaming\DDNet\types\` (sync destination)
  - `C:\Users\rust-\AppData\Roaming\DDNet\types\.ddnetcontrol-sync-state.json` (manifest)
  - `C:\Users\rust-\AppData\Roaming\DDNet\ddnet-server.sqlite` + `ddnet-cache.sqlite3` (must NOT change)
  - `C:\Users\rust-\AppData\Roaming\DDNet\maps\` + `downloadedmaps\` (must NOT change)
- DB backup (restore path): `C:\Users\rust-\AppData\Roaming\DDNet\.ddnetcontrol-backup-20260513-020207\`

## Evidence layout

All artifacts produced by this plan land under:

```
.planning/phases/01-harden-and-verify-sync-engine/
├── 01-PLAN.md                 (this file)
├── 01-CONTEXT.md              (existing)
├── 01-SUMMARY.md              (Task 3)
├── 01-VERIFICATION.md         (Task 3)
├── 01-VALIDATION.md           (Task 3)
└── evidence/                  (Task 2)
    ├── pre-snapshot.json
    ├── precheck-abort-report.json
    ├── full-sync-report.json
    ├── rerun-idempotent-report.json
    ├── interrupt-resume-report.md
    ├── post-snapshot.json
    ├── write-boundary-diff.txt
    ├── state-snapshot.json
    └── VERIFICATION-ERROR.txt (only present on failure)
```

---

## Tasks

### Task 1 — Narrow hardening of `tools/map_sync.py` and unit tests

**Goal**

Close the TEST-03 gap by adding URL pre-validation to `sync_testing_maps` so destructive `testingmaps/` replacement never starts if any remote URL is unreachable. Add a deterministic `official.files_count` field to the state file. Lock in atomicity, dedup, and pre-validation behavior with a unit test file so Phase 2+ can trust these contracts.

TDD: write tests first, red → green → commit.

**Requirements addressed:** TEST-03 (primary), SAFE-02 (regression guard), SYNC-03 (state file determinism).

**Steps**

1. Read `tools/map_sync.py` end-to-end and confirm:
   - `stream_download` already uses `tempfile.mkstemp` + `os.replace` with `temp_path.unlink()` on exception. If true, do not touch it. If not, fix it.
   - `collect_official_entries` filters `entry["type"] == "blob"` and paths starting with `types/`.
   - `resolve_testing_filename` dedupes via the `taken` set using ` (N)` suffix.

2. Add URL pre-validation to `sync_testing_maps` (TEST-03, per CONTEXT D-06). Implementation contract:
   - After `testing_payload` is fetched and `entries` is built, BUT BEFORE any write to `testing_root` or `temp_root` is attempted, iterate every entry and issue an HTTP HEAD via `urllib.request.Request(url, method="HEAD")`.
   - If HEAD returns 405 Method Not Allowed, retry with a 1-byte ranged GET (`Range: bytes=0-0`).
   - Treat 2xx/3xx as reachable. Treat 4xx/5xx and any `URLError`/`HTTPError`/socket timeout (5 s per URL) as unreachable.
   - If ANY URL is unreachable, raise `RuntimeError(f"Testing sync aborted — {n} URL(s) unreachable: {first_three_filenames}")` BEFORE `testing_root` is deleted or `temp_root` is written. `emit_progress(callback, stage="testing", message=..., counts={"unreachable": n})` before raising so the callback sees it.
   - On success path, log a `stage="testing", message="Pre-validated N URLs"` progress event and continue with existing behavior unchanged.
   - Skipped-URL handling: the spec says "skip a map entirely if its URL is unreachable, log the skip, continue with the rest" in CONTEXT D-06, BUT that conflicts with TEST-03's "validated before any local file is deleted or overwritten". Resolve: abort the WHOLE testing sync on the FIRST unreachable URL — safer. Re-running after upstream fixes the URL is cheap. Log all unreachable URLs in the error message for diagnosis.

3. Add `official.files_count` to `state["official"]` in `sync_official_types` right after `next_manifest` is finalized:
   ```python
   state["official"] = {
       "synced_at": ...,
       "upstream_tree_sha": tree_payload.get("sha"),
       "files": next_manifest if not dry_run else previous_files | next_manifest,
       "files_count": len(next_manifest if not dry_run else previous_files | next_manifest),
       "orphans": orphaned,
   }
   ```
   Keep `files` dict exactly as is — no rename, no schema break.

4. Create `tools/test_map_sync.py` using `unittest` (stdlib only, matches project convention — no external test deps). Tests:

   - `test_collect_official_entries_filters_types_and_builds_urls`: feed a synthetic tree payload with a mix of blob/tree entries, types/ and non-types/ paths, assert only blobs under `types/` are included and `download_url` uses `OFFICIAL_RAW_BASE + quote(path, safe="/")`.
   - `test_resolve_testing_filename_dedupes_collisions`: call `resolve_testing_filename` three times with the same derived filename, assert outputs are `Foo.map`, `Foo (1).map`, `Foo (2).map` and `taken` contains all three.
   - `test_resolve_testing_filename_appends_map_extension_when_missing`: URL path without `.map` suffix → filename gains `.map`.
   - `test_stream_download_cleans_tmp_on_interrupt`: monkey-patch `urllib.request.urlopen` to return an object whose read raises `KeyboardInterrupt` after yielding a few bytes, call `stream_download(url, dest)` inside a `with self.assertRaises(KeyboardInterrupt)`, then assert the parent dir contains NO `.ddnetcontrol-download-*` files and `dest` does not exist.
   - `test_stream_download_atomic_rename_on_success`: monkey-patch `urlopen` to return bytes, run `stream_download`, assert `dest` exists with correct bytes and no `.ddnetcontrol-download-*` orphans remain.
   - `test_sync_testing_maps_precheck_aborts_before_any_write`:
     - Build a temp `ddnet_root` under `tempfile.TemporaryDirectory()`; pre-create `types/testingmaps/existing.map` with known content.
     - Monkey-patch `request_json` to return a canned testing payload of two entries.
     - Monkey-patch `urllib.request.urlopen` so HEAD for the first URL returns 404 (use a `_FakeHTTPError` helper raising `urllib.error.HTTPError`).
     - Call `sync_testing_maps(types_root, state={"testing": {"files": {}}}, dry_run=False)`, assert it raises `RuntimeError` matching `/unreachable/`.
     - Assert `existing.map` still exists with original content.
     - Assert `types/.ddnetcontrol-testingmaps.tmp` was NOT created (or was cleaned).

5. Run the tests:
   ```powershell
   python tools\test_map_sync.py -v
   ```
   All tests pass. Zero network calls (all HTTP stubbed).

6. Manual smoke: `python tools\map_sync.py --mode official --dry-run --json | python -c "import sys,json; d=json.load(sys.stdin); assert d['success']; print('smoke ok')"` — confirms nothing in the hardening broke the dry-run path.

**Verification**

- `python tools\test_map_sync.py -v` exits 0 with all test methods reporting `ok`.
- `grep -n "files_count" tools/map_sync.py` shows the new field written into `state["official"]`.
- `grep -n "method=\"HEAD\"\|Range: bytes=0-0\|unreachable" tools/map_sync.py` shows the pre-validation implementation.
- Dry-run smoke above prints `smoke ok`.
- `git diff --stat` shows changes limited to `tools/map_sync.py` and `tools/test_map_sync.py` (no other files touched).

**Commit**

```
feat(map-sync): add URL pre-validation and harden atomic write test coverage

- sync_testing_maps now pre-validates every URL via HEAD (fallback
  ranged GET on 405) before deleting testingmaps/ — aborts with a
  RuntimeError on first 4xx/5xx/network error (TEST-03).
- state["official"]["files_count"] recorded for deterministic
  post-run assertions without dict-length coupling.
- tools/test_map_sync.py covers: types/ filter, filename dedup,
  temp-rename atomicity under interrupt, pre-validation abort
  leaves existing testingmaps untouched.

Phase 1 / Plan 01 / Task 1.
Addresses: TEST-03, SAFE-02, SYNC-03.
```

---

### Task 2 — Execute the real verification matrix against live `%APPDATA%\DDNet\`

**Goal**

Produce the hard evidence the milestone auditor asked for: a real full official sync against the live upstream tree, an immediate idempotent rerun, an interrupt+resume test against a controlled temp tree, and a write-boundary audit proving the run touched nothing under `maps/`, `downloadedmaps/`, or either sqlite DB. All of it orchestrated by one driver script so the run is repeatable.

**Requirements addressed:** SYNC-01, SYNC-02, SYNC-03, SYNC-04, TEST-01, TEST-02, TEST-03, SAFE-01, SAFE-02, SAFE-03, SAFE-05.

**Steps**

1. Create `tools/verify_phase1.py` (new file, stdlib only). It takes no CLI args, uses `get_ddnet_root()` from `map_sync` to resolve `%APPDATA%\DDNet`, and writes all evidence under `.planning/phases/01-harden-and-verify-sync-engine/evidence/`. The script is idempotent and re-runnable; it rewrites evidence files each run.

2. Implement the 7 steps below as functions. Each step writes its own evidence file. A failed assertion writes `evidence/VERIFICATION-ERROR.txt` with the failing check + traceback, then `sys.exit(1)` so Task 3 picks it up and flips VERIFICATION frontmatter to `status: human_needed`.

   **Step 2.1 — Pre-snapshot** → `evidence/pre-snapshot.json`
   - SHA256 of `%APPDATA%\DDNet\ddnet-server.sqlite` and `ddnet-cache.sqlite3` (file may be absent — record as `null`, not an error).
   - For every file under `%APPDATA%\DDNet\maps\` and `%APPDATA%\DDNet\downloadedmaps\` (recursive), record `{relpath, size, mtime_ns}`.
   - JSON shape: `{"captured_at": iso_utc, "db_hashes": {...}, "maps": [...], "downloadedmaps": [...]}`.

   **Step 2.2 — Precheck-abort test** → `evidence/precheck-abort-report.json`
   - Subprocess-based test so the live sync state is untouched: spawn a short Python child that imports `map_sync`, monkey-patches `request_json` to return a canned testing payload with one entry whose URL resolves to a local HTTP server returning 404, and calls `sync_testing_maps` against a `tempfile.mkdtemp()` tree pre-populated with a sentinel `testingmaps/existing.map`.
   - Assert the child exits non-zero, stderr contains `unreachable`, and the sentinel file still exists with its original SHA256.
   - Write `{"passed": true, "child_exit": N, "stderr_excerpt": "...", "sentinel_intact": true}`.

   **Step 2.3 — Full official sync** → `evidence/full-sync-report.json`
   - Run: `python tools\map_sync.py --mode official --json` with NO `--ddnet-root` override (real APPDATA).
   - Capture stdout to `evidence/full-sync-report.json`; tee stderr to `evidence/full-sync-stderr.log`.
   - Expected runtime: 20–60 min depending on network (CONTEXT line). Do not impose a timeout.
   - Assertions:
     - `summary.success == true`
     - `summary.mode == "official"`
     - `summary.official.remote_file_count == summary.official.created + summary.official.updated + summary.official.skipped`
     - `summary.official.remote_file_count >= 2000` (upstream ~2412)
     - `summary.official.downloaded_bytes > 0` (this is the FIRST real run, not dry-run)
     - `summary.official.orphaned_local_files == 0` on first run (no prior manifest)

   **Step 2.4 — Idempotent rerun** → `evidence/rerun-idempotent-report.json`
   - Immediately re-run the identical command. Capture stdout.
   - Assertions (SYNC-03, SAFE-01):
     - `summary.success == true`
     - `summary.official.created == 0`
     - `summary.official.updated == 0`
     - `summary.official.downloaded_bytes == 0`
     - `summary.official.skipped == summary.official.remote_file_count`

   **Step 2.5 — Interrupt-and-resume test** → `evidence/interrupt-resume-report.md`
   - This runs against a TEMP tree via `--ddnet-root` override — NOT the live APPDATA — because killing the live sync mid-flight risks corrupting the real manifest.
   - Start a local `http.server.ThreadingHTTPServer` on `127.0.0.1:<random>` that serves 20 synthetic blobs (each 256 KB of zero bytes) from `/types/synthetic/<n>.map`. Monkey-patch the tree response by launching a tiny sidecar server that also serves a faked tree JSON; OR simpler: patch by environment — spawn the child with a `MAP_SYNC_TEST_TREE_URL` override IF the engine supports it, else stub via a wrapper script that imports `map_sync` and calls `sync_official_types` directly against the temp server.
   - Choose the simpler path: write a small in-process driver (inside `verify_phase1.py`) that bypasses `main()` and calls `sync_official_types` directly with `types_root=<tempdir>/types` after monkey-patching `OFFICIAL_TREE_URL` / `OFFICIAL_RAW_BASE` module globals to point at the local server.
   - Run the sync in a child `multiprocessing.Process`; watch the tempdir until 5+ `.map` files exist, then `process.terminate()` (SIGTERM on POSIX, `TerminateProcess` on Windows).
   - Post-kill assertions (SAFE-02):
     - Glob `<tempdir>/types/**/.ddnetcontrol-download-*` → must be empty (no orphaned temp files after cleanup, OR cleanup on next run is also acceptable — document which).
     - No `.map` file is zero bytes. `for f in <tempdir>/types/**/*.map: assert f.stat().st_size > 0`.
   - Resume: re-run `sync_official_types` on the same tempdir. Assert all 20 `.map` files present with correct sizes (256 KB each).
   - Write a markdown report: steps taken, files present pre/post kill, files present post-resume, pass/fail.

   **Step 2.6 — Post-snapshot + write-boundary diff** → `evidence/post-snapshot.json` + `evidence/write-boundary-diff.txt`
   - Re-capture everything from step 2.1.
   - Diff `pre` vs `post`:
     - `db_hashes.ddnet-server.sqlite` MUST be unchanged → SAFE-03.
     - `db_hashes.ddnet-cache.sqlite3` MUST be unchanged → SAFE-03.
     - `maps/` diff (by relpath+size+mtime_ns) MUST be empty → SAFE-05.
     - `downloadedmaps/` diff MUST be empty → SAFE-05.
   - Also snapshot `%APPDATA%\DDNet\types\` pre vs post and emit the diff: it MUST show ~2412 additions and zero deletions (SYNC-04 — no orphan removal).
   - `write-boundary-diff.txt` is a human-readable diff; each of the four boundary-preserving invariants is printed as a PASS/FAIL line so `grep -c '^PASS' evidence/write-boundary-diff.txt` returns 4.

   **Step 2.7 — State-file check** → `evidence/state-snapshot.json`
   - Read `%APPDATA%\DDNet\types\.ddnetcontrol-sync-state.json` after both sync runs.
   - Assertions:
     - `state.official.files` is a dict with `>= 2000` entries (upstream ~2412) → SYNC-03, SAFE-01.
     - `state.official.files_count == len(state.official.files)` → Task 1 field present.
     - `state.official.upstream_tree_sha` is a 40-char hex string.
     - `state.official.orphans == []` on first run.
     - Sample 3 entries: each has keys `sha`, `size`, `source_path`, `download_url` and `source_path` starts with `types/`.
   - Write a compact snapshot (don't dump the full 2412-entry dict — record `files_count`, first-10 keys, last-10 keys, and the full `upstream_tree_sha` / `synced_at` / `orphans`).

3. Run the script:
   ```powershell
   python tools\verify_phase1.py
   ```
   Expect 30–70 minutes end-to-end (the bulk is step 2.3).

4. If any assertion fails, the script writes `evidence/VERIFICATION-ERROR.txt` with the failing check + Python traceback and exits 1. Do NOT delete this file — Task 3 reads it.

**Verification**

- `evidence/pre-snapshot.json`, `evidence/precheck-abort-report.json`, `evidence/full-sync-report.json`, `evidence/rerun-idempotent-report.json`, `evidence/interrupt-resume-report.md`, `evidence/post-snapshot.json`, `evidence/write-boundary-diff.txt`, `evidence/state-snapshot.json` all exist.
- `evidence/VERIFICATION-ERROR.txt` does NOT exist on success.
- `jq '.success' evidence/full-sync-report.json` prints `true`. (If `jq` is not available, a Python one-liner does the same.)
- `jq '.official.downloaded_bytes' evidence/rerun-idempotent-report.json` prints `0`.
- `grep -c '^PASS' evidence/write-boundary-diff.txt` prints `4` (server DB, cache DB, maps/, downloadedmaps/ all unchanged).
- `python -c "import json; s=json.load(open(r'C:\\Users\\rust-\\AppData\\Roaming\\DDNet\\types\\.ddnetcontrol-sync-state.json','r',encoding='utf-8')); print(s['official']['files_count'])"` prints a number ≥ 2000.

**Commit**

```
test(phase-1): execute verification matrix — real full sync, incremental, interrupt-resume, write-boundary

- tools/verify_phase1.py orchestrates the 7-step matrix against
  live %APPDATA%\DDNet\ and a temp tree for the interrupt test.
- Evidence written under
  .planning/phases/01-harden-and-verify-sync-engine/evidence/:
  pre/post snapshots, full sync report, idempotent rerun,
  precheck-abort, interrupt-resume, write-boundary diff,
  state snapshot.
- Confirms SYNC-01..04, TEST-01..03, SAFE-01/02/03/05.

Phase 1 / Plan 01 / Task 2.
```

---

### Task 3 — Author phase artifacts: SUMMARY / VERIFICATION / VALIDATION

**Goal**

Convert the evidence produced by Task 2 into the three per-phase artifacts the milestone audit gate consumes. VERIFICATION.md is the mechanical requirement→evidence table. VALIDATION.md is the Nyquist must-haves table. SUMMARY.md is the human-readable handoff for Phase 2+.

This task has a `checkpoint: human-verify` gate: once the three files are written and committed, pause and let the operator sanity-check before marking the phase done.

**Requirements addressed:** closes the traceability loop for all 11 requirements in this plan's frontmatter.

**Steps**

1. Read every file under `.planning/phases/01-harden-and-verify-sync-engine/evidence/`. If `VERIFICATION-ERROR.txt` exists, record the failing check text verbatim.

2. Write `01-VERIFICATION.md` with this exact frontmatter:
   ```yaml
   ---
   phase: 01-harden-and-verify-sync-engine
   status: passed  # or human_needed if VERIFICATION-ERROR.txt exists or any evidence file missing
   verified_at: <iso-utc>
   verifier: automated+human-verify
   ---
   ```
   Body: a requirement→evidence table with columns `| id | must-have text (verbatim from REQUIREMENTS.md) | actual | evidence path | pass/fail |`. One row per requirement:

   | id | must-have | evidence path |
   |----|-----------|---------------|
   | SYNC-01 | Sync upstream `types/` into `%APPDATA%\DDNet\types` | `evidence/full-sync-report.json` (official.created > 0) + `evidence/state-snapshot.json` |
   | SYNC-02 | Upstream folder structure preserved | `evidence/state-snapshot.json` (sample entries' `source_path` starts with `types/<category>/`) |
   | SYNC-03 | Only new/changed files redownloaded | `evidence/rerun-idempotent-report.json` (downloaded_bytes=0, skipped==remote_file_count) |
   | SYNC-04 | Orphan files left untouched, no rename | `evidence/write-boundary-diff.txt` (types/ diff shows additions only, 0 deletions) + `evidence/state-snapshot.json` (orphans=[]) |
   | TEST-01 | Testing feed refresh into `types\testingmaps` | `evidence/precheck-abort-report.json` exercises the code path; full testing-mode run deferred per CONTEXT scope (document as partial — testing downloads not executed against live because precheck-abort is the destructive rail being verified; full happy-path testing sync is a Phase 1 follow-up if needed) |
   | TEST-02 | All-or-nothing atomic replacement via staged temp dir | Code path: `sync_testing_maps` uses `types/.ddnetcontrol-testingmaps.tmp`; evidence: `evidence/precheck-abort-report.json` confirms temp dir not created when URLs fail. |
   | TEST-03 | URLs validated before any delete/overwrite | `evidence/precheck-abort-report.json` (sentinel intact, stderr contains `unreachable`) + Task 1 unit test `test_sync_testing_maps_precheck_aborts_before_any_write` |
   | SAFE-01 | Local sync state enables skip of unchanged files | `evidence/state-snapshot.json` (files_count >= 2000) + `evidence/rerun-idempotent-report.json` |
   | SAFE-02 | Temp-then-rename, no half-written .map on interrupt | `evidence/interrupt-resume-report.md` (no zero-byte maps, no `.ddnetcontrol-download-*` orphans) + Task 1 unit tests |
   | SAFE-03 | Sync never reads/writes `ddnet-cache.sqlite3` | `evidence/write-boundary-diff.txt` line `PASS: ddnet-cache.sqlite3 SHA256 unchanged` |
   | SAFE-05 | Never touches `maps/`, `downloadedmaps/`, uploaded custom maps | `evidence/write-boundary-diff.txt` lines `PASS: maps/ unchanged` and `PASS: downloadedmaps/ unchanged` |

   For TEST-01, if the happy-path live testing sync was not run, mark status `partial` in the verification row and list it in SUMMARY.md caveats.

3. Write `01-VALIDATION.md` using the Nyquist template at `~/.kiro/get-shit-done/templates/VALIDATION.md`. Must-haves:
   - `must_haves.truths`: "Sync writes only under types/**", "Rerun on unchanged upstream downloads 0 bytes", "Interrupted download leaves no half-written .map", "Testing sync aborts before delete on unreachable URL", "Neither DB file changes SHA256 across sync".
   - `must_haves.artifacts`: list every `evidence/*.json|md|txt` file.
   - `must_haves.key_links`: "state.official.files_count ↔ state.official.files dict length", "precheck RuntimeError ↔ sentinel file intact", "full-sync official.remote_file_count ↔ created+updated+skipped".
   Each must-have in the Nyquist table with `satisfied (y/n) | evidence | notes` columns.

4. Write `01-SUMMARY.md`:
   - **What changed in code** (Task 1): one-paragraph description of `sync_testing_maps` pre-validation + `state.official.files_count` + the new `tools/test_map_sync.py`.
   - **What was verified** (Task 2): the 7-step matrix, bullet list with the headline number from each (bytes downloaded first run, bytes downloaded rerun, files in state, write-boundary diff result).
   - **Remaining caveats**: any `partial` rows in VERIFICATION.md, the happy-path live testing sync if deferred, the fact that the interrupt-resume test uses a temp tree not live APPDATA (intentional — documented).
   - **Cross-phase hand-off notes for Phase 2+**:
     - Phase 2 can trust SAFE-03 and SAFE-05 contracts are enforced — `maps/` and both DB files were byte-identical across a full sync in live conditions.
     - Phase 2 can trust SAFE-02 (temp-then-rename atomicity) — verified by unit test AND interrupt-resume evidence.
     - Phase 2's `record_maps` inserts will see `>= 2000` files under `types/<category>/`, keyed by `Path(basename).stem` — confirmed by `state-snapshot.json`.
     - Phase 3 (website) and Phase 4 (native CLI) can treat `tools/map_sync.py --mode official --json` as the stable invocation contract; the summary JSON schema is the contract surface.
   - **Requirements closed**: checklist mirroring VERIFICATION.md.

5. Checkpoint: present the three files to the operator for human-verify. Prompt: "Read 01-VERIFICATION.md, 01-SUMMARY.md, 01-VALIDATION.md. Any row look wrong? Any evidence path invalid? Approve to proceed."

**Verification**

- `.planning/phases/01-harden-and-verify-sync-engine/01-SUMMARY.md`, `01-VERIFICATION.md`, `01-VALIDATION.md` all exist.
- `01-VERIFICATION.md` frontmatter `status` is either `passed` (all evidence present, no `VERIFICATION-ERROR.txt`) or `human_needed` (otherwise).
- Every requirement in this plan's frontmatter (SYNC-01..04, TEST-01..03, SAFE-01/02/03/05) appears exactly once in the VERIFICATION table.
- Every evidence-path cell in the VERIFICATION table resolves to a real file (`test -f` each one).
- VALIDATION.md Nyquist table has one row per item in `must_haves.truths`, `must_haves.artifacts`, `must_haves.key_links` — no empty cells.
- `git status` shows only the three new docs staged; no stray files.

**Commit**

```
docs(phase-1): SUMMARY/VERIFICATION/VALIDATION — Phase 1 complete

- 01-VERIFICATION.md maps each of SYNC-01..04, TEST-01..03,
  SAFE-01/02/03/05 to a specific evidence artifact from
  evidence/; status=passed on clean run or human_needed
  if VERIFICATION-ERROR.txt present.
- 01-VALIDATION.md Nyquist table of must-haves vs evidence.
- 01-SUMMARY.md code changes + what was verified + caveats
  + Phase 2-4 hand-off notes (SAFE-02/03/05 contracts are
  now trustable upstream).

Checkpoint: human-verify.

Phase 1 / Plan 01 / Task 3.
```

---

## Success criteria

This plan is complete when:

1. `tools/map_sync.py` has URL pre-validation in `sync_testing_maps` and `state.official.files_count` written on every non-dry-run.
2. `tools/test_map_sync.py` exists and `python tools\test_map_sync.py -v` exits 0.
3. `%APPDATA%\DDNet\types\` is populated with `>= 2000` `.map` files spread across category subfolders.
4. `%APPDATA%\DDNet\types\.ddnetcontrol-sync-state.json` has `official.files_count >= 2000` and a valid 40-char `upstream_tree_sha`.
5. `%APPDATA%\DDNet\ddnet-server.sqlite` and `ddnet-cache.sqlite3` have identical SHA256 before and after the sync run (pre-snapshot vs post-snapshot).
6. `%APPDATA%\DDNet\maps\` and `downloadedmaps\` are byte-identical before and after (relpath + size + mtime_ns).
7. `.planning/phases/01-harden-and-verify-sync-engine/evidence/` contains all 8 expected artifacts and NO `VERIFICATION-ERROR.txt`.
8. `01-SUMMARY.md`, `01-VERIFICATION.md`, `01-VALIDATION.md` exist and the operator has approved the human-verify checkpoint.
9. Three atomic commits landed on the phase branch with the messages specified in each task.

## Handoff

After success, Phase 2 can rely on these contracts without re-verification:

- SAFE-02: atomic write via temp-then-rename is covered by unit test + live interrupt-resume evidence.
- SAFE-03: sqlite DBs untouched by sync — proven by SHA256 boundary diff.
- SAFE-05: `maps/` and `downloadedmaps/` untouched by sync — proven by file-list boundary diff.
- SYNC-03: state-file-driven skip is proven by a zero-byte idempotent rerun immediately after a real full sync.

Phase 2 scope (`storage.cfg` install + `record_maps` INSERT OR IGNORE) begins from this verified baseline.
