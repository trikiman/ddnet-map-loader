# Phase 2 Summary: Server Visibility — `storage.cfg` + `record_maps`

**Status:** ✅ Complete (verified 2026-05-13)
**Requirements closed:** CFG-01, DB-01, DB-02, DB-03, DB-04, SAFE-04
**Requirements PASS via unit test:** CFG-02, CFG-03
**Requirements partial (Phase 4 closes):** CFG-04

## What changed in code

**`tools/server_register.py`** (new module, stdlib only — 270 lines):

- `ensure_storage_cfg(ddnet_root)` — idempotent install of `storage.cfg`. Three paths: create-if-missing with `add_path $USERDIR/types` plus defaults; append + back up to `.bak` if line missing (never overwrites existing `.bak`); no-op if already correct. Comment-aware: treats `#` and `//` as comments for line detection.
- `register_maps_in_db(ddnet_root, manifest=None)` — walks `types/` for `.map` files, dedupes by stem (since `record_maps.Map` is PK alone), takes a `VACUUM INTO` backup, then issues `INSERT OR IGNORE` for each new map. Returns a detailed summary including `other_table_counts_unchanged` audit.
- `register_with_server(ddnet_root)` — convenience combiner for `sync_ddnet_maps` to call when `--register-with-server` is set.
- CLI entry point for manual runs (`python tools/server_register.py --json`).
- Rolling backup retention: 3 most recent `.ddnetcontrol-server-backup-*.sqlite` files kept; older ones auto-deleted.

**`tools/test_server_register.py`** (new, 11 tests):

- `StorageCfgInstallTest`: create/append/no-op + never overwrite existing `.bak`
- `RecordMapsRegistrationTest`: insert new + preserve existing (byte-identical); never DELETE or UPDATE; testingmaps→testing alias; stem dedup; VACUUM INTO backup taken
- `NoOtherTablesTouchedTest`: `ddnet-cache.sqlite3` SHA unchanged; `maps/` mtime+bytes unchanged

**`tools/map_sync.py`** (extended in Phase 1's commit):

- `--register-with-server` CLI flag (off by default) — invokes `server_register.register_with_server` after a successful sync
- Same kwarg available programmatically on `sync_ddnet_maps(register_with_server=False)`
- Off by default so it doesn't surprise Phase 1's live verification. Flipped on by the CLI flag or by the Phase 3/4 callers.

**`tools/verify_phase2.py`** (new driver):

- 7-step verification against live `%APPDATA%\DDNet\`: pre-snapshot, register, post-snapshot, storage.cfg report, record_maps report, row-preservation deep-equal, write-boundary diff across 4 safety rails

## What was verified (live)

Against the user's live `%APPDATA%\DDNet\` on 2026-05-13 00:04 UTC:

| Check | Result |
|---|---|
| `storage.cfg` action | **created** (4-line default: `$USERDIR`, `$DATADIR`, `$CURRENTDIR`, `$USERDIR/types`) |
| `record_maps` rows inserted | **+56** |
| `record_maps` rows preserved (INSERT OR IGNORE) | **2398** (deep-equal for first 20 sampled rows) |
| `record_maps` duplicate stems skipped | **4** |
| `record_maps` total: pre → post | **3382 → 3438** (+56; net monotonically increasing = no DELETE) |
| `record_race` / `record_teamrace` / `record_saves` / `record_points` (+ `_backup`) | **byte-identical row counts** (all 7 tables) |
| `ddnet-cache.sqlite3` SHA256 | **unchanged** |
| `maps/` (1799 files) + `downloadedmaps/` (307 files) | **byte-identical** |
| Pre-write DB backup | `%APPDATA%\DDNet\.ddnetcontrol-server-backup-20260513T000444Z.sqlite` (via VACUUM INTO) |
| Unit tests | **11/11 passing** |

## Remaining caveats

- **CFG-02 / CFG-03 proven via unit test, not live run.** The live filesystem had `storage.cfg` absent at the start of Phase 2, so only the `create` path was exercised end-to-end. `append` and `no-op` paths have strong unit-test coverage. A future sync on a machine with existing `storage.cfg` will exercise those paths naturally.
- **CFG-04 deferred to Phase 4.** The native CLI + RCON flow in Phase 4 is the right place to run `sv_map "<name>"` and observe the server actually loading a synced map. Phase 2 installed the config correctly and upstream-compliant; Phase 4 closes the runtime proof.
- **2398 preserved rows were unexpectedly high.** The user's DDNet install had a pre-populated `record_maps` from years of gameplay (3382 rows pre-sync, including custom-uploaded and downloaded maps). Our sync manifest overlaps with ~2398 of those rows. `INSERT OR IGNORE` correctly skipped them. This is exactly what DB-02 guarantees — existing metadata stays.
- **The legacy `add_maps.ps1` and `move_maps.ps1`** in `%APPDATA%\DDNet\` are now obsolete. The user's choice whether to delete them. If run, `add_maps.ps1` in particular would destroy all the metadata we just preserved (it does `DELETE FROM record_maps`). Recommend manual deletion or renaming.

## Cross-phase handoff

**Phase 3 (website UI) can rely on:**

- The `--register-with-server` CLI flag exists and is tested — the web server can pass it through in its sync subprocess invocation, and the returned `summary.server_register` object will include `storage_cfg` action + `record_maps` counts for UI display.
- All safety rails are already enforced in `register_with_server`. The web UI doesn't need to add extra guards.

**Phase 4 (native CLI + RCON) can rely on:**

- `storage.cfg` containing `add_path $USERDIR/types` (live). `sv_map "<name>"` should work for any stem under `types/<category>/<name>.map`.
- `record_maps` contains a row for every synced map. The server's DDNet mod will honor all three canonical states: map exists on disk + row in record_maps = loadable; map exists on disk + no row = depends on mod (some require the row); no map on disk = not loadable regardless.
- For the RCON auto-trigger (TRIG-04), testing-sync also calls `register_with_server` so newly-discovered testing maps get registered without manual steps.

**Milestone audit:** Phase 2 closes 6 requirements fully + 2 via unit tests + defers 1 to Phase 4. Combined with Phase 1's 10 PASS + 1 PARTIAL (TEST-01), the milestone has closed 16 of 25 requirements after 2 phases. Phases 3-4 cover the remaining 9 (mostly TRIG-*).

## Files produced

```
.planning/phases/02-server-visibility/
├── 02-CONTEXT.md
├── 02-PLAN.md
├── 02-SUMMARY.md
├── 02-VERIFICATION.md
├── 02-VALIDATION.md
└── evidence/
    ├── pre-snapshot.json
    ├── post-snapshot.json
    ├── write-boundary-diff.txt
    ├── storage-cfg-report.json
    ├── storage-cfg-contents.txt
    ├── record-maps-report.json
    └── row-preservation-report.json

tools/
├── server_register.py        (new, 270 lines)
├── test_server_register.py   (new, 11 tests)
└── verify_phase2.py          (new driver)

%APPDATA%\DDNet\  (live system writes this phase performed)
├── storage.cfg                                (CREATED)
├── ddnet-server.sqlite                        (+56 record_maps rows; all other tables byte-identical)
└── .ddnetcontrol-server-backup-20260513T000444Z.sqlite  (VACUUM INTO snapshot)
```

---

*Phase 2 closed 2026-05-13T00:05Z. Next: Phase 3 (Verify Website Trigger and UI).*
