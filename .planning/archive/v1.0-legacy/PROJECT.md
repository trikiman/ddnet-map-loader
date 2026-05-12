# DDNet Control

## What This Is

DDNet Control is a Windows-first helper workspace for managing DDNet maps locally. It already supports browser-based uploads, local map browsing, file-association driven map loading, and native hot-reload of the current server map; this milestone extends it with automatic sync of official type maps and testing maps into the local DDNet data directory.

## Core Value

Move the right DDNet maps into the right local folders quickly and safely, without manual copy work or accidental map loss.

## Current Milestone: v1.0 Map Type Auto Sync

**Goal:** Add a reliable sync flow that pulls official type maps and DDNet testing maps into the local DDNet folder tree, with website and CLI/native triggers.

**Target features:**
- Incremental sync of upstream `ddnet-maps/types/` content into `C:\Users\rust-\AppData\Roaming\DDNet\types`
- Full refresh sync of testing maps from `https://twdata.pati.ga/maplists/ddnet-testing.json` into `C:\Users\rust-\AppData\Roaming\DDNet\types\testingmaps`
- Website-triggered sync with visible progress and final status
- Native/CLI trigger for the same sync flow
- Local sync manifest/state storage without mutating unrelated DDNet SQLite databases

## Requirements

### Validated

- ✓ User can load a local `.map` file into the server through the native executable and hot-reload flow — existing `ddnet_control.cpp`
- ✓ User can upload a `.map` file through the website and save it into `%APPDATA%\DDNet\maps` — existing `web/server.py` + `web/script.js`
- ✓ User can start a local file watcher from the website to auto-upload a map on save — existing `auto_uploader.ps1` flow
- ✓ User can browse local map folders and download stored maps from the website — existing `web/server.py` + `web/script.js`

### Active

- [ ] Sync official `ddnet-maps/types/` content incrementally into the local `types` folder
- [ ] Refresh testing maps from the remote JSON feed into `types\testingmaps`
- [ ] Trigger the sync flow from the website
- [ ] Trigger the sync flow from the native/CLI entry point
- [ ] Persist sync state locally so unchanged upstream files are skipped on later runs

### Out of Scope

- Editing or generating `storage.cfg` — the live DDNet directory does not currently use a local `storage.cfg`, and the requested sync does not require changing it
- Re-downloading the entire official `types/` tree on every run — wasteful for a ~1 GB upstream set and explicitly rejected by milestone goals
- Mutating `ddnet-cache.sqlite3` or `ddnet-server.sqlite` as part of the sync flow — inspected schemas show those databases are unrelated to this feature
- In-game embedded execution inside the DDNet client itself — this repo can add a native/CLI trigger, but the client cannot directly execute arbitrary external code through this project alone

## Context

The current repo has two active runtimes: a native Windows executable in `ddnet_control.cpp` and an optional Python web server in `web/server.py`. The requested feature targets the live DDNet data directory at `C:\Users\rust-\AppData\Roaming\DDNet`, where `types\` already exists and `types\testingmaps\` exists but is empty. The inspected local DDNet folder has no `storage.cfg`; it does have `ddnet-cache.sqlite3` and `ddnet-server.sqlite`, but those store ping cache and server record data rather than map sync metadata.

Upstream sync sources for this milestone are:

- `https://api.github.com/repos/ddnet/ddnet-maps/git/trees/master?recursive=1` filtered to `types/`
- `https://twdata.pati.ga/maplists/ddnet-testing.json`

The official `types/` tree is large, around 2,465 tracked blobs and roughly 1.08 GB, so an incremental manifest-based sync is required. The testing feed is small enough to replace fully on each run.

## Constraints

- **Tech stack**: Keep the existing Windows C++ executable and Python web server architecture — the repo already depends on both paths
- **Data safety**: Do not overwrite unrelated DDNet data outside `types\` and `types\testingmaps` — the user asked for targeted sync only
- **Performance**: Skip unchanged official upstream files on later syncs — the full official payload is too large for blind refreshes
- **Compatibility**: Leave `storage.cfg` untouched unless a proven requirement appears — local inspection shows it is absent
- **State management**: Avoid mutating unrelated DDNet SQLite databases without a confirmed consumer — current schemas do not justify it

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Use a local sync manifest/state file under `types\` | Needed to track upstream blobs and skip unchanged official files safely | ✓ Good |
| Mirror upstream `types/` relative paths instead of flattening files | Upstream structure includes per-type config and `maps/` subtrees, not just raw `.map` files | ✓ Good |
| Leave `ddnet-cache.sqlite3` and `ddnet-server.sqlite` untouched | Inspected schemas show ping cache and record storage, not map sync metadata | ✓ Good |
| Expose sync through both website and native/CLI trigger | Matches requested trigger surfaces and reuses one shared sync engine | ✓ Good |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `$gsd-transition`):
1. Requirements invalidated? -> Move to Out of Scope with reason
2. Requirements validated? -> Move to Validated with phase reference
3. New requirements emerged? -> Add to Active
4. Decisions to log? -> Add to Key Decisions
5. "What This Is" still accurate? -> Update if drifted

**After each milestone** (via `$gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check - still the right priority?
3. Audit Out of Scope - reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-24 after implementing milestone v1.0 Map Type Auto Sync*
