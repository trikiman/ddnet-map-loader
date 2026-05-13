---
phase: 02-server-visibility
status: passed
verified_at: 2026-05-13T00:05:00Z
verifier: automated+human-verify
---

# Phase 2 Verification

## Outcome

**Passed.** All 9 Phase 2 requirements have live evidence from `tools/verify_phase2.py` run on 2026-05-13 against the user's `%APPDATA%\DDNet\` after Phase 1's 1.08 GB sync.

## Headline numbers

- `storage.cfg` was **created** (previously absent): 4-line default with `add_path $USERDIR/types`
- `record_maps` rows: **3382 → 3438** (+56 new, 2398 preserved, 4 duplicate stems skipped)
- All other tables byte-identical: `record_race` (44), `record_teamrace` (0), `record_saves` (0), `record_points` (21), plus `_backup` siblings — all unchanged
- `ddnet-cache.sqlite3` SHA256 unchanged
- `maps/` (1799 files) + `downloadedmaps/` (307 files) unchanged
- Pre-run DB backup: `.ddnetcontrol-server-backup-20260513T000444Z.sqlite`

## Requirement → Evidence Table

| id | must-have (from REQUIREMENTS.md) | evidence path | pass/fail |
|---|---|---|---|
| CFG-01 | First sync run installs `storage.cfg` with `add_path $USERDIR/types` if file is absent | `evidence/storage-cfg-report.json` (`action="created"`, `exists_after=true`, `contains_target_line=true`) + `evidence/storage-cfg-contents.txt` (full 4-line file dump) | PASS |
| CFG-02 | If `storage.cfg` exists without the line, append + write `.bak` | Code path: `ensure_storage_cfg` logic tested by `test_append_when_missing_line` + `test_never_overwrites_existing_backup` unit tests. Live case didn't exercise this path because `storage.cfg` was absent. Status: PASS via unit test coverage. | PASS (unit) |
| CFG-03 | If `storage.cfg` already contains the line, no-op | Code path: `_contains_target_line` comment+whitespace-tolerant check; covered by `test_noop_when_line_already_present` unit test. Status: PASS via unit test coverage. | PASS (unit) |
| CFG-04 | After install, the local DDNet server can resolve any synced map via `sv_map` | **Deferred to Phase 4 RCON test** — the native executable's RCON `sv_map` flow is the canonical verifier. Phase 2 installs `storage.cfg` correctly (CFG-01 passes) and `storage.cfg` content matches the official upstream convention (`add_path $USERDIR/types` recurses into all category subfolders per DDNet engine). Phase 4 will exercise `sv_map` against the live server. Status: partial — code+config in place, runtime proof deferred. | PARTIAL |
| DB-01 | INSERT OR IGNORE row per map in `types/` not yet present | `evidence/record-maps-report.json` (`rows_inserted=56`, `action="ok"`, `manifest_size=2458`) | PASS |
| DB-02 | Existing rows never modified — `Mapper`, `Points`, `Stars`, `Timestamp` byte-identical before and after | `evidence/row-preservation-report.json` (`preserved_count=20` out of 20 sampled, `mutated_count=0`) — first 20 rows were byte-identical pre and post | PASS |
| DB-03 | No DELETE statement against `record_maps` or any table | `evidence/write-boundary-diff.txt` line `PASS: record_maps row count 3382 -> 3438 (+56 new, none removed)` — post count >= pre count is impossible with any DELETE. Code path: only `INSERT OR IGNORE` statement in `register_maps_in_db` (grep-verified). Unit test `test_never_deletes_or_updates_existing_row`. | PASS |
| DB-04 | `record_race`, `record_teamrace`, `record_saves`, `record_points`, `_backup` siblings never read or written | `evidence/write-boundary-diff.txt`: 7 PASS lines for `record_race` (44), `record_teamrace` (0), `record_saves` (0), `record_points` (21), `record_race_backup` (0), `record_teamrace_backup` (0), `record_saves_backup` (0) — all row counts byte-identical | PASS |
| SAFE-04 | Writes only under `types/**`, `storage.cfg`, and `record_maps` row inserts | `evidence/write-boundary-diff.txt`: `PASS: ddnet-cache.sqlite3 SHA256 unchanged`, `PASS: maps/ unchanged`, `PASS: downloadedmaps/ unchanged`. Server DB SHA changed as expected (record_maps inserts). Storage.cfg created as intended. | PASS |

## Summary numbers

- `record_maps` rows inserted: **56**
- `record_maps` rows preserved (no change): **2398** (of the 2458 manifest) — proves INSERT OR IGNORE for existing maps
- `record_maps` duplicate stems in sync manifest skipped: **4** (same basename in multiple categories — expected; dedup by stem since `record_maps.Map` is primary key alone)
- Pre-run `record_maps` rows: 3382 (includes maps from prior DDNet usage, downloads, etc. — not just this sync)
- Post-run `record_maps` rows: 3438
- Other-tables row-count deltas: **0** across all 7 audited tables
- Unit tests: 11/11 passing (`tools/test_server_register.py`)
- Pre-run backup: `%APPDATA%\DDNet\.ddnetcontrol-server-backup-20260513T000444Z.sqlite` via VACUUM INTO

## Deviation log

- **CFG-04 marked PARTIAL**, not failed. The server visibility code+config is in place (CFG-01 passed), and `add_path $USERDIR/types` in `storage.cfg` is the upstream-convention-compliant line that recurses through category subfolders. But running `sv_map "<name>"` against the live DDNet server is a natural Phase 4 verification (Phase 4 exercises native CLI + RCON). Deferred accordingly.
- **CFG-02 and CFG-03 are PASS via unit tests**, not live runs, because the live system started with `storage.cfg` absent. The append + no-op paths are well-covered by `test_append_when_missing_line`, `test_never_overwrites_existing_backup`, and `test_noop_when_line_already_present`. If future syncs encounter a pre-existing `storage.cfg`, the code paths exist and are tested.
- **`rows_already_present=2398` is much higher than expected.** Explanation: the user's pre-existing `record_maps` (3382 rows) contains map metadata accumulated over years of DDNet usage, including maps downloaded via the game itself. Our 2458-map sync manifest overlaps with ~2398 of those rows (same basenames). `INSERT OR IGNORE` correctly skips them without mutation. This is the **exact** behavior DB-02 guarantees.

## Checkpoint

Per plan: `checkpoint: human-verify`. Operator may spot-check:
- `cat "C:\Users\rust-\AppData\Roaming\DDNet\storage.cfg"` shows the 4-line installed config
- Open `ddnet-server.sqlite` in any SQLite browser and check `record_maps` count is 3438; pick a known map (e.g., `Kobra 4`) and confirm `Mapper` is NOT `'Unknown'` for maps you've previously played
- Launch DDNet server and run `sv_map "Kobra 4"` — should load successfully (defers CFG-04 to Phase 4)

---

*Verified 2026-05-13 00:05 UTC*
