# DDNet Control

## In Plain Words

DDNet Control is a set of tools you already use to manage DDNet maps on your Windows PC: a small app (`ddnet_control.exe`) that talks to your local DDNet server, and a website (`web/`) for uploading maps from your browser.

This milestone adds one new thing: a **Map Auto Sync**. It does four jobs:

1. **Downloads** every official DDNet map (the ones from https://github.com/ddnet/ddnet-maps) into `C:\Users\rust-\AppData\Roaming\DDNet\types\`. On later runs, it only downloads maps that actually changed — it doesn't re-download the whole 1 GB tree every time.
2. **Refreshes** the DDNet testing-maps list (a small set that changes often) into `types\testingmaps\`.
3. **Writes one line to `storage.cfg`** so your local DDNet server can actually find those maps. Without that line, the server looks in the wrong place.
4. **Adds new maps to your server's map list** (`record_maps` table in `ddnet-server.sqlite`) so the server knows they exist. Your existing points, stars, and mapper info stay exactly the way they are. Nothing gets deleted or overwritten — only new rows are added.

You can start the sync in three ways:
- Click a button on the website.
- Run `ddnet_control.exe --sync-types` (or `--sync-types-testing` or `--sync-types-official`).
- Let it happen automatically: whenever the server changes map, the sync quietly refreshes the testing maps. It's debounced so rapid-fire map changes don't cause multiple syncs at once.

What it **never** does:
- Delete or change anything in your existing server records (your finish times, points, saves, teamraces).
- Touch `ddnet-cache.sqlite3` at all (that file is for server browser pings, nothing to do with maps).
- Delete local maps when they disappear from GitHub upstream — they stay in your `types/` folder.
- Touch your `maps/` folder where your custom uploaded maps live.

## Core Value

Move the right DDNet maps into the right local folders quickly and safely, without manual copy work, without losing any existing server data.

## Current Milestone: v1.0 Map Type Auto Sync

**Goal:** Ship the Map Auto Sync described above — website button, CLI flags, auto-trigger on map change, plus the `storage.cfg` fix and safe `record_maps` registration — and produce the audit evidence the previous attempt lacked.

**Target features:**
- Download upstream `ddnet/ddnet-maps types/` incrementally into `C:\Users\rust-\AppData\Roaming\DDNet\types`
- Refresh testing maps from `https://twdata.pati.ga/maplists/ddnet-testing.json` into `types\testingmaps`
- Install one line in `storage.cfg` so the server finds synced maps
- Register new maps in `record_maps` (add-only, never delete, never overwrite)
- Website button with visible progress and result
- Native CLI flags with logged results
- Auto-trigger testing-sync after RCON map change, with debounce

## Requirements

### Validated (already shipped and working)

- ✓ User can load a local `.map` file into the server through the native executable and hot-reload flow — `ddnet_control.cpp`
- ✓ User can upload a `.map` file through the website and save it into `%APPDATA%\DDNet\maps` — `web/server.py` + `web/script.js`
- ✓ User can start a local file watcher from the website to auto-upload a map on save — `auto_uploader.ps1`
- ✓ User can browse local map folders and download stored maps from the website — `web/server.py` + `web/script.js`

### Active (this milestone)

- [ ] Download the upstream official map tree into the local `types` folder, skipping files that already match
- [ ] Refresh testing maps from the remote JSON feed into `types\testingmaps`
- [ ] Install `storage.cfg` with `add_path $USERDIR/types` if that line is absent
- [ ] Add rows for new maps to `record_maps` (INSERT OR IGNORE only — never touch existing rows)
- [ ] Start the sync from the website with visible progress and result
- [ ] Start the sync from the native CLI and log the outcome
- [ ] Auto-trigger testing-sync after an RCON map change, with debounce

### Out of Scope

- Deleting or updating existing rows in `record_maps` — preserves player Points/Stars/Mapper
- Any write to `record_race`, `record_teamrace`, `record_saves`, `record_points`, or their `_backup` siblings — those are player finish records
- Any write to `ddnet-cache.sqlite3` — unrelated to maps
- Writing anywhere under `maps/` or `downloadedmaps/` — user custom maps stay untouched
- Deleting local maps when upstream removes them — leave in place
- Re-downloading the full official tree on every run — ~1.08 GB, incremental-only
- Auto-triggering full official sync on every map change — risks GitHub 60-req/hr rate limit; only testing-sync is cheap enough
- Embedded in-client sync command — not reachable from this repo

## Context

The repo has two active runtimes:
- Native Windows executable from `ddnet_control.cpp` — talks to DDNet server over RCON
- Python web server `web/server.py` — sync endpoints and browser UI

The feature targets `C:\Users\rust-\AppData\Roaming\DDNet`. Current state of that directory:
- `types\` exists but only has `testingmaps\` populated (46 maps from a successful testing sync) plus a legacy sync-state file
- `storage.cfg` is **absent** — this is why the server can't currently load maps from `types/` and why the old `add_maps.ps1` + `move_maps.ps1` scripts existed as a workaround
- `ddnet-server.sqlite` has `record_maps` (map metadata: mapper, points, stars) and five record-tracking tables (race, teamrace, saves, points) plus `_backup` versions — this milestone writes to `record_maps` only, and only with INSERT OR IGNORE
- `ddnet-cache.sqlite3` has one table `server_pings`, untouched by this milestone
- `maps\` has user-uploaded custom maps, untouched by this milestone

Upstream sources:
- Official: `https://api.github.com/repos/ddnet/ddnet-maps/git/trees/master?recursive=1` filtered to `types/` (2412 `.map` files, ~1.08 GB, all unique basenames across categories)
- Testing: `https://twdata.pati.ga/maplists/ddnet-testing.json` (~46 maps)

Reference: the official `ddnet/ddnet-maps` repo ships a `storage.cfg` listing each category by name, but DDNet's engine walks subdirectories under any added path — so the single line `add_path $USERDIR/types` covers every current and future category.

## Constraints

- **Tech stack:** Keep the existing Windows C++ executable and Python web server
- **Data safety:** No writes to any record table except `record_maps`, and `record_maps` is INSERT OR IGNORE only. No writes to `ddnet-cache.sqlite3`. No writes under `maps/`. Writes limited to `types/**`, `storage.cfg` (create or append once with `.bak`), and `record_maps` rows
- **Performance:** Skip unchanged official files via SHA+size compare; never re-download full tree blindly
- **Rate limits:** Unauthenticated GitHub API is 60 req/hr; auto-trigger runs testing-sync only (single JSON fetch, no tree call)
- **Idempotency:** Every step must produce the same result on re-run; no non-deterministic suffixes, no destructive DB writes, no move-instead-of-copy
- **Reversibility:** Single `storage.cfg` line can be removed without consequence; sync state file can be deleted to force a full re-check; `record_maps` rows we added can be identified by mapper=Unknown stamp if needed later

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Keep local sync state file under `types/` | Tracks upstream blob SHAs so re-runs skip unchanged files | ✓ Carried from legacy |
| Mirror upstream `types/` layout (no flatten) | Upstream tree has category subfolders; flattening destroys metadata | ✓ Carried from legacy |
| Install `storage.cfg` with `add_path $USERDIR/types` | DDNet's storage engine resolves maps by walking added paths; one line covers every category recursively | NEW |
| Register new maps in `record_maps` via INSERT OR IGNORE | User experience confirms server needs the row to treat the map as real; INSERT OR IGNORE preserves existing metadata | NEW — corrects the legacy approach which did DELETE+INSERT and wiped Points/Stars |
| Never write to other record tables | Those are player finish records and cannot be safely managed by sync | NEW |
| Auto-trigger is testing-sync only | Full official sync can hit GitHub rate limit; testing is cheap | NEW |
| Trigger after RCON map change (not file-watcher saves) | Editor saves fire too often; RCON hot-reload fires once per real map switch | NEW |
| Leave orphaned local maps in place | Destructive removal risks data loss; upstream removals are rare | NEW |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase:**
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions

**After each milestone:**
1. Full review of all sections
2. Core Value check
3. Audit Out of Scope reasons
4. Update Context with current state

---
*Last updated: 2026-05-12 — fresh start of milestone v1.0 Map Type Auto Sync after archiving the legacy v1.0 attempt (see `.planning/archive/v1.0-legacy/`)*
