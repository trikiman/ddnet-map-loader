# State

## Project Reference

See: `.planning/PROJECT.md` (updated 2026-05-13)

**Core value:** Move the right DDNet maps into the right local folders quickly and safely, without manual copy work, without accidental map loss, and without destructive edits to existing DDNet data.
**Current focus:** Milestone v1.0 COMPLETE — pending final audit + archive

## Current Position

Phase: All 4 phases COMPLETE
Plan: `.planning/ROADMAP.md`
Status: Ready for `/gsd-audit-milestone` + `/gsd-complete-milestone`
Last activity: 2026-05-13 — Phase 4 committed (f217663). Milestone v1.0 audit-ready.

## Phase Status

| # | Phase | Status | Commit | Requirements |
|---|-------|--------|--------|--------------|
| 1 | Harden and Verify Sync Engine | ✅ PASSED | 9195de8 | SYNC-01..04, TEST-02/03, SAFE-01/02/03/05 (10 PASS, 1 PARTIAL = TEST-01) |
| 2 | Server Visibility — storage.cfg + record_maps | ✅ PASSED | d0314df | CFG-01, DB-01..04, SAFE-04 (6 PASS, 2 PASS-via-unit = CFG-02/03, 1 PARTIAL = CFG-04) |
| 3 | Verify Website Trigger and UI | ✅ PASSED | 82bf6c1 | TRIG-01, TRIG-02 (2 PASS) |
| 4 | Native CLI + RCON Auto-Sync | ✅ PASSED | f217663 | TRIG-03, TRIG-04, SAFE-06 (3 PASS) |

## Milestone Scorecard

- **Requirements closed (PASS or PASS-via-unit): 23 / 25**
- **Partial (external conditions): 2 / 25** — CFG-04 (needs live DDNet server sv_map test), TEST-01 (live upstream has broken URL, safety rail held in its place)
- **Failed: 0 / 25**

## Accumulated Context

Milestone v1.0 (Map Type Auto Sync) end-to-end flow:

1. **Sync engine** (`tools/map_sync.py`, Phase 1): pulls upstream official `types/` incrementally (SHA + size manifest), pulls testing maps with TEST-03 URL pre-validation, atomic writes via temp-then-rename, orphan sweep on startup
2. **Server visibility** (`tools/server_register.py`, Phase 2): installs `storage.cfg` with `add_path $USERDIR/types`; INSERT OR IGNORE new maps into `record_maps`; VACUUM INTO backup before any DB write; rolling 3-backup retention
3. **Website trigger** (`web/server.py`, Phase 3): `/sync-types` POST accepts `all`/`official`/`testing`; `/sync-status` GET exposes queued → running → success/error state machine; 409 on concurrent requests; 400 on invalid mode. Phase 2 runs automatically on website-triggered syncs.
4. **Native trigger** (`ddnet_control.cpp`, Phase 4): `--sync-types-*` flags with venv→py-3→python fallback; post-RCON-map-change auto-trigger fires detached testing-only sync; 60 s debounce via `.ddnetcontrol-last-auto-sync` marker

### Safety rails enforced and verified end-to-end

- `maps/` (1799 files): byte-identical before/after full sync (Phase 1 write-boundary)
- `downloadedmaps/` (307 files): byte-identical before/after full sync (Phase 1)
- `ddnet-cache.sqlite3`: SHA256 unchanged across any sync + DB write (Phases 1, 2, 3)
- `ddnet-server.sqlite`: only `record_maps` INSERT OR IGNORE; all other tables (record_race/teamrace/saves/points + `_backup` siblings) row counts byte-identical (Phase 2)
- Existing `record_maps` rows byte-identical for Mapper/Points/Stars/Timestamp (Phase 2: 2398 pre-existing rows preserved, 56 new inserted)
- Testing sync never deletes `testingmaps/` when any URL is unreachable (Phases 1, 3, 4: safety rail held in production with a live broken URL)

### Key numbers

- Upstream: 2468 files (~2412 `.map` + 56 config files), 1,086,272,160 bytes (1.08 GB), tree SHA `14b4b9936f02da830f3ceaddc54f49ceec336cbf`
- Full sync time: 1513 s (25 min), idempotent rerun: 0.8 s (0 bytes)
- Local record_maps total: 3382 → 3438 (+56 new)
- Legacy workflow obsolete: `%APPDATA%\DDNet\add_maps.ps1` and `move_maps.ps1` are no longer needed (user-owned, not deleted)

### Pre-phase backups (recovery paths)

- `.ddnetcontrol-backup-20260513-020207/` — full pre-milestone snapshot (DBs + sync state)
- `.ddnetcontrol-server-backup-20260513T000444Z.sqlite` — VACUUM INTO snapshot taken before Phase 2's first DB write

---
*Last updated: 2026-05-13 after Phase 4 commit f217663. Milestone v1.0 AUDIT-READY.*
