# State

## Project Reference

See: `.planning/PROJECT.md` (updated 2026-04-24)

**Core value:** Move the right DDNet maps into the right local folders quickly and safely, without manual copy work or accidental map loss.
**Current focus:** Milestone v1.0 verification and handoff

## Current Position

Phase: Milestone v1.0 complete
Plan: `.planning/ROADMAP.md`
Status: Implemented and verified
Last activity: 2026-04-24 - Website trigger, native trigger, and sync engine verified

## Accumulated Context

- The repo already has a codebase map under `.planning/codebase/`.
- The live DDNet directory contains `types\`; `types\testingmaps\` was initially empty before milestone verification.
- `storage.cfg` is not present in the live DDNet directory.
- `ddnet-cache.sqlite3` stores only `server_pings`.
- `ddnet-server.sqlite` stores record tables and is not the right place for sync state.
- The upstream official `types/` tree is about 1.08 GB, so incremental sync is required.
- The real testing-map sync was executed successfully and wrote 46 maps into `C:\Users\rust-\AppData\Roaming\DDNet\types\testingmaps`.
- The official `types/` sync path was verified via dry-run against the live upstream tree; the first full download was not executed during verification because it is roughly 1.08 GB.
- The native executable path was verified using `ddnet_control.exe --sync-types-testing`.

---
*Last updated: 2026-04-24 after implementing and verifying milestone v1.0 Map Type Auto Sync*
