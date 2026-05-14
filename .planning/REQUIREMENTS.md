# Requirements: DDNet Control

**Defined:** 2026-05-12
**Milestone:** v1.0 Map Type Auto Sync
**Core Value:** Move the right DDNet maps into the right local folders quickly and safely, without manual copy work and without losing any existing server data.

## In Plain Words

What this milestone delivers, as user-visible behaviors:

1. **I can click a button on the website and my local DDNet folder fills up with every official map.** The first run downloads everything; later runs only download what changed.
2. **I can run `ddnet_control.exe --sync-types` and the same thing happens, without opening a browser.**
3. **After I sync, my local DDNet server can actually load those maps** (right now, without `storage.cfg`, it can't).
4. **When I switch maps on my server via RCON, the testing-maps list refreshes itself in the background** — so I get newly released testing maps without thinking about it.
5. **Nothing I had before gets lost.** Custom uploaded maps stay in `maps/`. My points, finish records, and saves stay exactly where they were. Maps that upstream removes stay in my local folder.

The requirements below are the precise, testable version of those five sentences.

## v1.0 Requirements

### Official Type Sync

- [x] **SYNC-01**: User can sync the upstream `ddnet/ddnet-maps types/` tree into `C:\Users\rust-\AppData\Roaming\DDNet\types`
- [x] **SYNC-02**: Synced files keep the upstream folder structure (`types/novice/*.map`, `types/brutal/*.map`, etc. mirror the upstream layout exactly)
- [x] **SYNC-03**: Only files that are new or changed upstream since the last successful sync are re-downloaded (SHA + size compare against the local manifest)
- [x] **SYNC-04**: Any file not in the upstream manifest is left untouched — no orphan deletion, no renaming of user files

### Testing Map Sync

- [ ] **TEST-01**: User can refresh testing maps from `https://twdata.pati.ga/maplists/ddnet-testing.json` into `C:\Users\rust-\AppData\Roaming\DDNet\types\testingmaps`
- [x] **TEST-02**: The testing-map refresh replaces the contents of `testingmaps` in one atomic run (all-or-nothing via a staged temp directory)
- [x] **TEST-03**: Remote map URLs are validated before any local file is deleted or overwritten

### Server Visibility — `storage.cfg`

- [x] **CFG-01**: First sync run installs `%APPDATA%\DDNet\storage.cfg` with the line `add_path $USERDIR/types` if the file is absent
- [x] **CFG-02**: If `storage.cfg` exists but doesn't contain `add_path $USERDIR/types`, the sync appends the line and writes a one-time backup to `storage.cfg.bak` (never overwriting an existing `.bak`)
- [x] **CFG-03**: If `storage.cfg` already contains `add_path $USERDIR/types` (exact or whitespace-variant), both files are left untouched
- [x] **CFG-04**: After `storage.cfg` is installed, the local DDNet server can resolve any synced map by name (e.g. `sv_map "Kobra 4"`) and load it from `types/<category>/`

### Server Map Registration — `record_maps`

- [x] **DB-01**: For each map present in `types/` after sync that does not yet have a row in `ddnet-server.sqlite -> record_maps`, the sync inserts a row via `INSERT OR IGNORE` with `Map=<basename>, Server=<category or 'DDNet'>, Mapper='Unknown', Points=0, Stars=0`
- [x] **DB-02**: Existing `record_maps` rows are never modified — `Mapper`, `Points`, `Stars`, `Timestamp` of any row that was already present stay byte-identical before and after sync
- [x] **DB-03**: No `DELETE` statement is ever executed against `record_maps` or any other table in `ddnet-server.sqlite`
- [x] **DB-04**: Tables `record_race`, `record_teamrace`, `record_saves`, `record_points`, and their `_backup` siblings are never read or written — sync does not open them

### Triggers

- [x] **TRIG-01**: User can start the sync from the website with selectable mode (official, testing, or both)
- [x] **TRIG-02**: Website shows sync progress and final result (per-file status, byte counts, success/error state)
- [x] **TRIG-03**: User can start the same sync from the native CLI (`ddnet_control.exe --sync-types-official`, `--sync-types-testing`, `--sync-types`)
- [x] **TRIG-04**: The native executable auto-triggers a testing-only sync after a successful RCON hot-reload map change, without blocking the map change itself

### Safety

- [x] **SAFE-01**: Local sync state under `%APPDATA%\DDNet\types\.ddnetcontrol-sync-state.json` lets later official syncs skip unchanged upstream files
- [x] **SAFE-02**: Every downloaded file is written via temp-then-rename so an interrupted run leaves no half-written `.map`
- [x] **SAFE-03**: Sync never reads or writes `ddnet-cache.sqlite3`
- [x] **SAFE-04**: Sync writes only under: `types/**`, `storage.cfg` (create or append with `.bak`), and `record_maps` rows (INSERT OR IGNORE only)
- [x] **SAFE-05**: Sync never touches `maps/`, `downloadedmaps/`, or any user-uploaded custom maps
- [x] **SAFE-06**: The auto-trigger (TRIG-04) coalesces map changes within a short window into a single sync run (debounce, no thrash)

## Future Requirements

### Runtime Integration (v1.1+)

- **RUNT-01**: Trigger sync directly from an in-game command without switching to an external executable
- **RUNT-02**: Schedule background syncs on a cadence (hourly, daily)
- **RUNT-03**: Optional fetch of authoritative `record_maps` metadata from an upstream catalog to fill in Mapper/Points/Stars (still INSERT OR IGNORE; never overwrite existing)

## Out of Scope

| Feature | Reason |
|---------|--------|
| DELETE or UPDATE existing `record_maps` rows | Legacy `add_maps.ps1` did this and wiped player Points/Stars/Mapper. Preserving existing rows is a hard constraint. |
| Any write to `record_race`, `record_teamrace`, `record_saves`, `record_points`, or `_backup` tables | Those are player finish records and cannot be safely synthesized by sync |
| Any write to `ddnet-cache.sqlite3` | Only contains `server_pings`, unrelated to maps |
| Flattening `types/` into `maps/` | Unnecessary once `storage.cfg` adds `$USERDIR/types`; legacy `move_maps.ps1` becomes obsolete |
| Deleting orphaned local maps | If upstream removes a map, the local copy stays to avoid data loss |
| Re-downloading full official tree on every run | Upstream is ~1.08 GB; incremental is mandatory |
| Auto-triggering full official sync on map change | Risks GitHub unauthenticated API rate-limit (60 req/hr) |
| Embedded sync command inside the DDNet client | Not reachable from this repo; native CLI is the substitute |
| Editing `autoexec_server.cfg`, `settings_ddnet.cfg`, or similar DDNet configs | Out of scope; only `storage.cfg` is installed, only when missing or incomplete |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| SYNC-01 | Phase 1 | ✅ PASS |
| SYNC-02 | Phase 1 | ✅ PASS |
| SYNC-03 | Phase 1 | ✅ PASS |
| SYNC-04 | Phase 1 | ✅ PASS |
| TEST-01 | Phase 1 | 🟡 PARTIAL (external: live upstream URL broken) |
| TEST-02 | Phase 1 | ✅ PASS |
| TEST-03 | Phase 1 | ✅ PASS |
| CFG-01 | Phase 2 | ✅ PASS |
| CFG-02 | Phase 2 | ✅ PASS (unit test) |
| CFG-03 | Phase 2 | ✅ PASS (unit test) |
| CFG-04 | Phase 2 | ✅ PASS (live econ change_map across 5 maps in 4 categories, 2026-05-14) |
| DB-01 | Phase 2 | ✅ PASS |
| DB-02 | Phase 2 | ✅ PASS |
| DB-03 | Phase 2 | ✅ PASS |
| DB-04 | Phase 2 | ✅ PASS |
| TRIG-01 | Phase 3 | ✅ PASS |
| TRIG-02 | Phase 3 | ✅ PASS |
| TRIG-03 | Phase 4 | ✅ PASS |
| TRIG-04 | Phase 4 | ✅ PASS (live: ddnet_control.log auto-sync entries since 2026-05-13) |
| SAFE-01 | Phase 1 | ✅ PASS |
| SAFE-02 | Phase 1 | ✅ PASS |
| SAFE-03 | Phase 1 | ✅ PASS |
| SAFE-04 | Phase 2 | ✅ PASS |
| SAFE-05 | Phase 1 | ✅ PASS |
| SAFE-06 | Phase 4 | ✅ PASS |

**Coverage:**
- v1.0 requirements: 25 total
- Mapped to phases: 25 ✓
- PASS or PASS (unit test): 24 / 25
- PARTIAL (external conditions): 1 / 25
- FAIL: 0 / 25

---
*Requirements defined: 2026-05-12 — fresh start after archiving legacy v1.0*
*Re-verified 2026-05-14 after post-audit hardening (commits 602ee30, fca71de, ce3c3e6, 0cb23c7) — CFG-04 promoted from PARTIAL to PASS.*
