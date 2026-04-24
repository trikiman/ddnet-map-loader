# State

## Project Reference

See: `.planning/PROJECT.md` (updated 2026-04-24)

**Core value:** Move the right DDNet maps into the right local folders quickly and safely, without manual copy work or accidental map loss.
**Current focus:** Phase 4 - Complete Official Types Sync

## Current Position

Phase: 4 - Complete Official Types Sync
Plan: `.planning/ROADMAP.md`
Status: Gap closure planned
Last activity: 2026-04-24 - Added gap-closure phases from milestone audit

## Accumulated Context

- The repo already has a codebase map under `.planning/codebase/`.
- The live DDNet directory contains `types\`.
- The local `types\` root currently contains only `testingmaps\` and `.ddnetcontrol-sync-state.json`; it does not yet contain the upstream official type directories like `brutal`, `dummy`, `novice`, or `solo`.
- `storage.cfg` is not present in the live DDNet directory.
- `ddnet-cache.sqlite3` stores only `server_pings`.
- `ddnet-server.sqlite` stores record tables and is not the right place for sync state.
- The upstream official `types/` tree is about 1.08 GB, so incremental sync is required.
- The real testing-map sync was executed successfully and wrote 46 maps into `C:\Users\rust-\AppData\Roaming\DDNet\types\testingmaps`.
- The official `types/` sync path was verified via dry-run against the live upstream tree; the first full download was not executed during verification because it is roughly 1.08 GB.
- The native executable path was verified using `ddnet_control.exe --sync-types-testing`.

---
*Last updated: 2026-04-24 after planning milestone gap-closure phases*
