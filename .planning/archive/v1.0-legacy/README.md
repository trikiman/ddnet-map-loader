# v1.0 Legacy Archive

These artifacts were produced during an initial attempt at milestone v1.0 (Map Type Auto Sync) that was built **without GSD execution artifacts** (no per-phase SUMMARY/VERIFICATION/VALIDATION files). The milestone audit `v1.0-MILESTONE-AUDIT.md` flagged every requirement as orphaned under the workflow.

Rather than patch it with "gap closure" phases, the milestone was restarted cleanly. See `.planning/PROJECT.md` and `.planning/ROADMAP.md` at the repo root for the active v1.0 plan.

## Contents

- `PROJECT.md` — original project definition (2026-04-24)
- `REQUIREMENTS.md` — original SYNC/TEST/TRIG/SAFE requirements
- `ROADMAP.md` — original 3 phases + 3 gap-closure phases
- `v1.0-MILESTONE-AUDIT.md` — the audit that exposed the gaps
- `phases/` — empty legacy phase directories (04, 05, 06)

## Implementation carried over

The following code shipped as part of the legacy attempt and is kept in the active repo. The new milestone verifies and hardens it rather than rebuilding:

- `tools/map_sync.py` — incremental official sync, full-replace testing sync, local state, lock
- `web/server.py` — `/sync-types` and `/sync-status` endpoints
- `web/index.html`, `web/script.js` — sync controls and status polling
- `ddnet_control.cpp` — `--sync-types`, `--sync-types-official`, `--sync-types-testing` CLI flags

Runtime evidence at archive time:

- `C:\Users\rust-\AppData\Roaming\DDNet\types\.ddnetcontrol-sync-state.json` — testing manifest populated, official manifest empty (only dry-runs executed)
- `C:\Users\rust-\AppData\Roaming\DDNet\types\testingmaps\` — 46 `.map` files from a successful testing sync

## Known issues to address in the fresh milestone

- Official full sync (~1.08 GB) has never actually been executed — only dry-runs
- No browser-level end-to-end verification recorded
- Native sync required fallback from broken repo venv to system Python
- `compile.bat` needed repair for MSVC shell contamination
