---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: Milestone v1.0 restarted — requirements defined, roadmap next
last_updated: "2026-05-12T22:16:11.776Z"
last_activity: 2026-05-12
progress:
  total_phases: 4
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
---

# State

## Project Reference

See: `.planning/PROJECT.md` (updated 2026-05-12)

**Core value:** Move the right DDNet maps into the right local folders quickly and safely, without manual copy work, without accidental map loss, and without destructive edits to existing DDNet data.
**Current focus:** Defining milestone v1.0 roadmap (fresh start after archiving the legacy attempt)

## Current Position

Phase: Not started (defining roadmap)
Plan: `.planning/ROADMAP.md` (pending)
Status: Milestone v1.0 restarted — requirements defined, roadmap next
Last activity: 2026-05-12

## Accumulated Context

- Legacy v1.0 was archived to `.planning/archive/v1.0-legacy/` because it shipped without GSD execution artifacts (no per-phase SUMMARY/VERIFICATION/VALIDATION); the audit `v1.0-MILESTONE-AUDIT.md` flagged every requirement as orphaned.
- Legacy code carries over and will be verified/hardened rather than rebuilt:
  - `tools/map_sync.py` — incremental official sync, full-replace testing sync, local state, lock file
  - `web/server.py` — `/sync-types` and `/sync-status` endpoints
  - `web/index.html`, `web/script.js` — sync controls and status polling
  - `ddnet_control.cpp` — `--sync-types`, `--sync-types-official`, `--sync-types-testing` CLI flags
- Codebase maps in `.planning/codebase/` remain valid.
- Runtime state at milestone restart:
  - `C:\Users\rust-\AppData\Roaming\DDNet\types\.ddnetcontrol-sync-state.json` — testing manifest populated (46 maps), official manifest empty (only dry-runs executed against the 1.08 GB upstream)
  - `C:\Users\rust-\AppData\Roaming\DDNet\types\testingmaps\` — 46 `.map` files from a successful testing sync
  - `C:\Users\rust-\AppData\Roaming\DDNet\storage.cfg` — absent (root cause of why the local server cannot currently serve synced maps)
  - `C:\Users\rust-\AppData\Roaming\DDNet\maps\` — hundreds of user custom-uploaded maps (out of scope for sync)
  - `ddnet-cache.sqlite3` — single table `server_pings` (unrelated to maps)
  - `ddnet-server.sqlite` — record/ranking tables including `record_maps` (metadata only, not map existence)
- Key correction from the legacy attempt: DDNet's server finds maps by filesystem scan through `storage.cfg` add_paths, AND the server's DDNet mod treats a map as "real" only when it has a `record_maps` row (user-confirmed). So the sync needs two writes: install `storage.cfg` with `add_path $USERDIR/types`, and `INSERT OR IGNORE` new rows into `record_maps`. Never DELETE, never UPDATE, never touch other record tables.
- Upstream `ddnet-maps` tree currently has 2412 `.map` files under `types/` totaling ~1.08 GB; all basenames are unique across categories (verified against live API).

## Known Technical Debt Carried From Legacy

- Official full sync has never actually been executed — only dry-runs against the 1.08 GB payload.
- No browser-level end-to-end verification of the website sync flow was recorded.
- Native sync required fallback from broken repo venv launcher to system Python.
- `compile.bat` needed local repair to work around MSVC shell contamination.
- Legacy `add_maps.ps1` and `move_maps.ps1` in `%APPDATA%\DDNet\` become obsolete once `storage.cfg` is installed; document but do not delete.

---
*Last updated: 2026-05-12 after milestone v1.0 fresh-start*
