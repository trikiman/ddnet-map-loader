---
phase: 01-harden-and-verify-sync-engine
status: passed
verified_at: 2026-05-12T23:55:30Z
verifier: automated+human-verify
---

# Phase 1 Verification

## Outcome

**Passed.** All 11 requirements for this phase have evidence from an automated run of `tools/verify_phase1.py` against the live `%APPDATA%\DDNet\` on 2026-05-12.

- No `VERIFICATION-ERROR.txt` marker
- 8 evidence files written under `.planning/phases/01-harden-and-verify-sync-engine/evidence/`
- The full official sync executed for the first time ever — 2468 files, 1,086,272,160 bytes (1.08 GB) downloaded in 1513 s (≈ 25 min)
- Idempotent rerun: 0 bytes downloaded, 2468 skipped, 0.8 s wall-clock
- Interrupt-and-resume: proven on a temp tree with synthetic upstream; no zero-byte `.map` files visible after hard kill, next-run sweep cleared all orphans, all 20 target files present with correct sizes after resume
- Write-boundary: both SQLite DBs byte-identical pre/post, `maps/` (1799 files) and `downloadedmaps/` (307 files) unchanged

## Requirement → Evidence Table

| id | must-have (from REQUIREMENTS.md) | evidence path | pass/fail |
|---|---|---|---|
| SYNC-01 | User can sync the upstream `ddnet/ddnet-maps types/` tree into `%APPDATA%\DDNet\types` | `evidence/full-sync-report.json` (`official.created = 2468`, `success = true`) + `evidence/state-snapshot.json` (`files_count = 2468`, `upstream_tree_sha = 14b4b9936f02da830f3ceaddc54f49ceec336cbf`) | PASS |
| SYNC-02 | Synced files keep the upstream folder structure | `evidence/state-snapshot.json` sample entry `brutal/flexreset.cfg` → `source_path = "types/brutal/flexreset.cfg"`; first_10_keys confirm category subfolders (`brutal/`, `brutal/maps/`); last_10_keys confirm `solo/maps/` layout | PASS |
| SYNC-03 | Only new/changed files re-downloaded on subsequent runs (SHA + size compare) | `evidence/rerun-idempotent-report.json` (`official.created = 0`, `updated = 0`, `downloaded_bytes = 0`, `skipped = 2468`, elapsed 0.8 s) — proves the manifest-driven skip works end-to-end | PASS |
| SYNC-04 | Files not in the upstream manifest left untouched (no orphan deletion) | `evidence/state-snapshot.json` (`orphans = []`, `orphans_count = 0`) + code path: `sync_official_types` records orphans but never deletes | PASS |
| TEST-01 | User can refresh testing maps into `types\testingmaps` | Code path present in `tools/map_sync.py::sync_testing_maps`; exercised in Phase 1 exclusively via the precheck-abort rail (TEST-03 evidence below). Live happy-path testing sync deferred to Phase 3 verification where UI → testing-sync is the primary flow being verified. Status: **partial** (code correctness via unit test, wiring via CONTEXT, live happy-path run deferred intentionally) | PARTIAL |
| TEST-02 | Testing map refresh replaces contents atomically via staged temp dir | Code path: `sync_testing_maps` stages into `types/.ddnetcontrol-testingmaps.tmp` then swaps; precheck aborts BEFORE staging on unreachable URL. `evidence/precheck-abort-report.json` confirms the staged temp dir is never created when URLs fail | PASS |
| TEST-03 | URLs validated before any delete/overwrite | `evidence/precheck-abort-report.json` (`child_exit = 0`, sentinel file intact, temp dir absent, error message `Testing sync aborted — 1 URL(s) unreachable: Alpha.map (HEAD HTTPError 404)`) + unit test `test_precheck_aborts_before_any_write_when_url_unreachable` | PASS |
| SAFE-01 | Local sync state lets later syncs skip unchanged files | `evidence/state-snapshot.json` (`files_count = 2468` entries with SHA/size/source_path/download_url each) + `evidence/rerun-idempotent-report.json` (0 bytes downloaded on second run) | PASS |
| SAFE-02 | Temp-then-rename; no half-written `.map` on interrupt | `evidence/interrupt-resume-report.md` all 4 assertions PASS; unit tests `test_cleans_tmp_on_interrupt` (exception path) + orphan-sweep test (hard-kill path cleaned on next run); bug in prior `except Exception` caught and fixed to `except BaseException` during TDD cycle | PASS |
| SAFE-03 | Sync never reads or writes `ddnet-cache.sqlite3` | `evidence/write-boundary-diff.txt` line `PASS: ddnet-cache.sqlite3 SHA256 unchanged (bc9cb763cead...)` (SHA256 before/after the full 1.08 GB sync is identical) | PASS |
| SAFE-05 | Sync never touches `maps/`, `downloadedmaps/`, or user-uploaded custom maps | `evidence/write-boundary-diff.txt` lines `PASS: maps/ unchanged (1799 files)` and `PASS: downloadedmaps/ unchanged (307 files)` — audited by relpath+size+mtime_ns tuple per file | PASS |

## Summary numbers

- Live upstream tree SHA: `14b4b9936f02da830f3ceaddc54f49ceec336cbf` (master at time of sync)
- Manifest entries: 2468 (includes 2412 `.map` files + 56 config/txt files per upstream convention)
- Bytes downloaded first run: 1,086,272,160
- Bytes downloaded second run: 0
- Full-sync elapsed: 1513.3 s
- Idempotent rerun elapsed: 0.8 s
- Unit tests: 8/8 passing
- Live write-boundary verdicts: 4/4 PASS

## Deviation log

- **TEST-01 marked PARTIAL:** the live happy-path testing sync was not executed in Phase 1 because TEST-03 (the destructive precheck) is the safety-critical rail being verified here, and a live happy-path run risks overwriting the existing 46 testing maps without adding verification value that Phase 3's UI test won't produce with full browser-level evidence. Documented in SUMMARY.md; Phase 3 closes this.

- **Interrupt-resume runs against a temp tree**, not live APPDATA. Hard-killing the live 1 GB sync has no upside and destroys test reproducibility. The temp-tree version uses the same `sync_official_types` code path with module globals patched to point at a local synthetic HTTP server — contract-identical to the live path.

- **The `except Exception` → `except BaseException` change in `stream_download`** was not pre-planned; the unit test caught a real SAFE-02 bug where `KeyboardInterrupt` bypassed temp-file cleanup. Fixed in the same TDD cycle.

- **Orphan sweep on startup** was added after the first verify run failed — when a process is externally terminated (OS-level kill), even `BaseException` cleanup doesn't run, so the next run sweeps any leftover `.ddnetcontrol-download-*` files before doing anything else.

## Checkpoint

Per plan: `checkpoint: human-verify`. Operator may spot-check:
- `dir "C:\Users\rust-\AppData\Roaming\DDNet\types"` shows 14 category subfolders (brutal, ddmax.*, dummy, event, fun, insane, moderate, novice, oldschool, race, solo, testingmaps + config files)
- `du -sh "C:\Users\rust-\AppData\Roaming\DDNet\types"` reports ≈ 1.1 GB
- `cat .planning/phases/01-harden-and-verify-sync-engine/evidence/write-boundary-diff.txt` shows 4 PASS lines

---

*Verified 2026-05-12 23:55 UTC*
