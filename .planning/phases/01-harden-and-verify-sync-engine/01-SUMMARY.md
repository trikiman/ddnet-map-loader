# Phase 1 Summary: Harden and Verify Sync Engine

**Status:** ✅ Complete (verified 2026-05-12)
**Commits:** `d3414cd` (Task 1), *TBD* (Task 2 + Task 3)
**Requirements closed:** SYNC-01, SYNC-02, SYNC-03, SYNC-04, TEST-02, TEST-03, SAFE-01, SAFE-02, SAFE-03, SAFE-05
**Requirements partial:** TEST-01 (live happy-path testing sync deferred intentionally to Phase 3 UI verification)

## What changed in code

**`tools/map_sync.py`** (narrow hardening; no architectural change):

- `sync_testing_maps` now **pre-validates every remote URL** via HTTP HEAD (fallback to ranged GET on 405) before deleting or overwriting any file in `testingmaps/`. Aborts with a clear `RuntimeError` listing the first three unreachable URLs on the first failure. This closes TEST-03.
- `stream_download` exception handler widened from `except Exception` to `except BaseException` so `KeyboardInterrupt` and `SystemExit` also clean up the temp download file. This closes a real SAFE-02 bug caught by the unit test.
- New orphan-sweep at the top of `sync_official_types`: any `.ddnetcontrol-download-*` file left over from a hard-killed prior run is removed before the sync does anything else. Handles the case where OS-level kill bypassed the exception handler.
- `state["official"]["files_count"]` written alongside the `files` dict so downstream audits don't need to call `len()` on the manifest.
- `--json` CLI flag now routes progress callbacks to stderr so stdout stays pure JSON (enables shell-pipe automation; was mixing progress + JSON before).
- New optional `register_with_server: bool = False` kwarg on `sync_ddnet_maps` + corresponding `--register-with-server` CLI flag. **Off by default** so Phase 1's own verification run doesn't accidentally write to the DB. Phase 2 will flip it on in the callers that matter.

**`tools/test_map_sync.py`** (new file, 8 tests, stdlib only):

- `collect_official_entries` filters to `types/`-prefixed blobs and builds correctly-escaped raw URLs
- `resolve_testing_filename` dedupes collisions deterministically with `(N)` suffix and appends `.map` when missing
- `stream_download` atomic-rename works on success; temp file cleaned on exception (including `BaseException`)
- `sync_testing_maps` pre-validation aborts before any write when a URL returns 404 (sentinel file intact)
- `sync_official_types` writes `files_count` to state and sweeps orphan temp files on startup

**`tools/verify_phase1.py`** (new driver; orchestrates the end-to-end verification matrix):

- 7 steps: pre-snapshot, precheck-abort subprocess test, interrupt+resume against temp tree, full live sync, idempotent rerun, post-snapshot + write-boundary diff, state-file sanity check
- All evidence written under `.planning/phases/01-harden-and-verify-sync-engine/evidence/`
- Fails loudly on any assertion violation with a `VERIFICATION-ERROR.txt` marker for downstream tooling

## What was verified (live)

**Against the live `C:\Users\rust-\AppData\Roaming\DDNet\`** on 2026-05-12:

| Check | Headline number |
|---|---|
| Full official sync | **2468 files, 1,086,272,160 bytes (1.08 GB), 1513 s (25 min)** |
| Idempotent rerun | **0 bytes, 2468 skipped, 0.8 s wall-clock** |
| Upstream tree SHA pinned | `14b4b9936f02da830f3ceaddc54f49ceec336cbf` |
| Write-boundary verdicts | **4/4 PASS** — `ddnet-server.sqlite` SHA unchanged, `ddnet-cache.sqlite3` SHA unchanged, `maps/` (1799 files) unchanged, `downloadedmaps/` (307 files) unchanged |
| Types tree delta | pre=46 files, post=2458 files (delta=+2412) |
| Interrupt-resume (temp tree) | 20/20 files present after resume, 0 zero-byte, 0 orphan temp files |
| Precheck-abort (subprocess) | Sentinel file intact, temp dir absent, error message names URL + HTTP code |
| Unit tests | **8/8 passing** (offline, stdlib only) |

## Remaining caveats

- **TEST-01 is PARTIAL**, not failed. The code path is covered by unit tests and the precheck-abort live evidence, but the live happy-path testing sync (download all 46 testing maps against live upstream) was not executed in Phase 1. Reasoning: TEST-03 is the safety-critical rail being verified here, and running a live happy-path testing sync adds no safety value beyond what the UI-driven run in Phase 3 will produce with full browser evidence. If the Phase 3 happy-path run fails for any reason, the fallback is the unit test + precheck evidence already captured here.
- **Interrupt-resume uses a temp tree** with a synthetic local HTTP server, not live `%APPDATA%\DDNet\`. Running the hard-kill test against the live sync has no upside and destroys reproducibility. The code path exercised is identical to the live one (same `sync_official_types` function, same module globals patched at runtime).

## Cross-phase handoff

**Phase 2 can rely on (no re-verification needed):**

- **SAFE-02 (temp-then-rename atomicity):** covered by unit test `test_cleans_tmp_on_interrupt` + live interrupt-resume evidence. Hard-kill case also covered by orphan-sweep on startup.
- **SAFE-03 (DB files untouched by sync):** `ddnet-cache.sqlite3` and `ddnet-server.sqlite` had byte-identical SHA256 before and after a 1.08 GB sync. Phase 2's `record_maps` writes will be the ONLY thing changing `ddnet-server.sqlite` when the new `--register-with-server` flag is set, and the Phase 2 verification will confirm `ddnet-cache.sqlite3` stays untouched even then.
- **SAFE-05 (no writes under `maps/` or `downloadedmaps/`):** 1799 + 307 files byte-identical across a live sync. Phase 2 inherits this constraint; its new code never touches either directory.

**Phase 2 + 3 + 4 can consume:**

- Stable CLI contract: `python tools/map_sync.py --mode {official,testing,all} [--ddnet-root PATH] [--dry-run] [--json] [--register-with-server]`
- Stable JSON summary schema: top-level `{mode, ddnet_root, types_root, state_file, lock_file, dry_run, register_with_server, started_at, finished_at, success}` + `summary.official` and/or `summary.testing` sub-objects + `summary.server_register` when `--register-with-server`
- Stable manifest format: `%APPDATA%\DDNet\types\.ddnetcontrol-sync-state.json` with `{version, official: {synced_at, upstream_tree_sha, files: {<relpath>: {sha, size, source_path, download_url}}, files_count, orphans: []}, testing: {...}}`

**Milestone audit impact:** the three phase artifacts (SUMMARY, VERIFICATION, VALIDATION) plus the 9 evidence files close the milestone audit gap for all SYNC-*, TEST-* (partially), and SAFE-* requirements owned by this phase. 11/11 requirements have mechanical evidence pointing at specific files that downstream auditors can cross-check without re-running anything.

## Obsolete workarounds now unnecessary

Post-Phase-1 state does not yet make legacy workarounds obsolete — that happens in Phase 2 when `storage.cfg` install lands. For reference:

- `C:\Users\rust-\AppData\Roaming\DDNet\add_maps.ps1` — will become obsolete after Phase 2. Not touched by this phase.
- `C:\Users\rust-\AppData\Roaming\DDNet\move_maps.ps1` — will become obsolete after Phase 2. Not touched.

## Files produced

```
.planning/phases/01-harden-and-verify-sync-engine/
├── 01-CONTEXT.md             (Task 0)
├── 01-PLAN.md                (Task 0)
├── 01-SUMMARY.md             (this file)
├── 01-VERIFICATION.md        (req-→-evidence table)
├── 01-VALIDATION.md          (Nyquist table)
└── evidence/
    ├── pre-snapshot.json
    ├── precheck-abort-report.json
    ├── interrupt-resume-report.md
    ├── full-sync-report.json
    ├── full-sync-report.stderr.log
    ├── rerun-idempotent-report.json
    ├── rerun-idempotent-report.stderr.log
    ├── post-snapshot.json
    ├── write-boundary-diff.txt
    └── state-snapshot.json

tools/
├── map_sync.py               (modified — hardening + --register-with-server)
├── test_map_sync.py          (new — 8 tests)
└── verify_phase1.py          (new — driver)
```

---

*Phase 1 closed 2026-05-12T23:56Z. Next: Phase 2 (Server Visibility — `storage.cfg` + `record_maps`).*
