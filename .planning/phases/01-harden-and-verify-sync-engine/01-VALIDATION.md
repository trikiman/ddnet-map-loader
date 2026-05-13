---
phase: 01-harden-and-verify-sync-engine
validated_at: 2026-05-12T23:56:00Z
nyquist_complete: true
---

# Phase 1 Validation (Nyquist)

Nyquist audit: every must-have claim in this phase is backed by an evidence artifact that a different process/observer could independently check. No single-source truth; every claim has a second witness.

## Must-have truths

| # | Truth | Satisfied | Primary evidence | Second witness |
|---|---|---|---|---|
| T-1 | Sync writes only under `types/**` and the sync state file | y | `evidence/write-boundary-diff.txt` (4 PASS lines for DBs + maps/ + downloadedmaps/) | `evidence/pre-snapshot.json` vs `evidence/post-snapshot.json` — raw mtime+size tuples for every file |
| T-2 | Rerun on unchanged upstream downloads 0 bytes | y | `evidence/rerun-idempotent-report.json` (`downloaded_bytes = 0`, `skipped = 2468`) | `evidence/rerun-idempotent-report.stderr.log` (only `[official] Fetching upstream` and `[official] Prepared official sync plan` lines, no `Downloading` lines) |
| T-3 | Interrupted download leaves no half-written `.map` visible | y | `evidence/interrupt-resume-report.md` assertion `PASS: no zero-byte .map files visible after kill` | unit test `test_cleans_tmp_on_interrupt` (different mechanism — exception unwinding) |
| T-4 | Testing sync aborts BEFORE deletion when an URL is unreachable | y | `evidence/precheck-abort-report.json` (`sentinel_intact = true`, `temp_dir_absent = true`, error message names URL + HTTP code) | unit test `test_precheck_aborts_before_any_write_when_url_unreachable` |
| T-5 | Both SQLite DBs are byte-identical across the full sync | y | `evidence/write-boundary-diff.txt` (`PASS: ddnet-server.sqlite SHA256 unchanged`, `PASS: ddnet-cache.sqlite3 SHA256 unchanged`) | `evidence/pre-snapshot.json` vs `evidence/post-snapshot.json` (`db_hashes` block — identical hex strings) |
| T-6 | Orphan temp files from hard-killed prior runs are swept on next run | y | `evidence/interrupt-resume-report.md` assertion `PASS: next-run sweep cleared all download orphans` | unit test `test_orphan_download_temp_files_swept_on_start` |

## Must-have artifacts

| Artifact | Path | Purpose |
|---|---|---|
| Pre-snapshot | `evidence/pre-snapshot.json` | SHA256 + file-list baseline before sync |
| Post-snapshot | `evidence/post-snapshot.json` | SHA256 + file-list after sync for diff |
| Write-boundary diff | `evidence/write-boundary-diff.txt` | Human-readable PASS/FAIL verdicts |
| Full-sync report | `evidence/full-sync-report.json` | JSON summary of the 1.08 GB live run |
| Full-sync stderr log | `evidence/full-sync-report.stderr.log` | Per-file progress lines for diagnosis |
| Idempotent rerun | `evidence/rerun-idempotent-report.json` | 0-byte rerun proof |
| Interrupt-resume | `evidence/interrupt-resume-report.md` | Temp-tree kill-and-recover walkthrough |
| Precheck-abort | `evidence/precheck-abort-report.json` | Sentinel-intact + temp-dir-absent after unreachable URL |
| State snapshot | `evidence/state-snapshot.json` | Compact view of `.ddnetcontrol-sync-state.json` after the run |

All artifacts are `ls -f` accessible under `.planning/phases/01-harden-and-verify-sync-engine/evidence/`.

## Must-have key links

| Link | Both ends | Verified |
|---|---|---|
| `official.files_count ↔ len(official.files)` in state file | `evidence/state-snapshot.json` fields `files_count = 2468` and `files_len = 2468` | y |
| `precheck RuntimeError ↔ sentinel file intact` | `evidence/precheck-abort-report.json` records both the error message (mentions `unreachable`) AND `sentinel_intact = true` in the same report | y |
| `full-sync official.remote_file_count ↔ created+updated+skipped` | `evidence/full-sync-report.json`: `remote_file_count = 2468`, `created = 2468`, `updated = 0`, `skipped = 0`; invariant holds (2468 = 2468 + 0 + 0) | y |
| `rerun official.skipped ↔ full-sync official.created` | Full run created 2468, rerun skipped 2468. Same number, proving the manifest correctly reflects what was downloaded. | y |
| `upstream_tree_sha ↔ unique synced snapshot` | `14b4b9936f02da830f3ceaddc54f49ceec336cbf` — 40-char hex, recorded in state file, pinned to the master commit in force at sync time. Rerun against a changed master would record a new SHA. | y |

## Nyquist completeness

Every must-have truth has at least two witnesses (live-run evidence + unit test, or two different live-evidence files). No single-source failure mode could hide a regression.

---

*Validated 2026-05-12 23:56 UTC*
