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

- [ ] **SYNC-01**: User can sync the upstream `ddnet/ddnet-maps types/` tree into `C:\Users\rust-\AppData\Roaming\DDNet\types`
- [ ] **SYNC-02**: Synced files keep the upstream folder structure (`types/novice/*.map`, `types/brutal/*.map`, etc. mirror the upstream layout exactly)
- [ ] **SYNC-03**: Only files that are new or changed upstream since the last successful sync are re-downloaded (SHA + size compare against the local manifest)
- [ ] **SYNC-04**: Any file not in the upstream manifest is left untouched — no orphan deletion, no renaming of user files

### Testing Map Sync

- [ ] **TEST-01**: User can refresh testing maps from `https://twdata.pati.ga/maplists/ddnet-testing.json` into `C:\Users\rust-\AppData\Roaming\DDNet\types\testingmaps`
- [ ] **TEST-02**: The testing-map refresh replaces the contents of `testingmaps` in one atomic run (all-or-nothing via a staged temp directory)
- [ ] **TEST-03**: Remote map URLs are validated before any local file is deleted or overwritten

### Server Visibility — `storage.cfg`

- [ ] **CFG-01**: First sync run installs `%APPDATA%\DDNet\storage.cfg` with the line `add_path $USERDIR/types` if the file is absent
- [ ] **CFG-02**: If `storage.cfg` exists but doesn't contain `add_path $USERDIR/types`, the sync appends the line and writes a one-time backup to `storage.cfg.bak` (never overwriting an existing `.bak`)
- [ ] **CFG-03**: If `storage.cfg` already contains `add_path $USERDIR/types` (exact or whitespace-variant), both files are left untouched
- [ ] **CFG-04**: After `storage.cfg` is installed, the local DDNet server can resolve any synced map by name (e.g. `sv_map "Kobra 4"`) and load it from `types/<category>/`

### Server Map Registration — `record_maps`

- [ ] **DB-01**: For each map present in `types/` after sync that does not yet have a row in `ddnet-server.sqlite -> record_maps`, the sync inserts a row via `INSERT OR IGNORE` with `Map=<basename>, Server=<category or 'DDNet'>, Mapper='Unknown', Points=0, Stars=0`
- [ ] **DB-02**: Existing `record_maps` rows are never modified — `Mapper`, `Points`, `Stars`, `Timestamp` of any row that was already present stay byte-identical before and after sync
- [ ] **DB-03**: No `DELETE` statement is ever executed against `record_maps` or any other table in `ddnet-server.sqlite`
- [ ] **DB-04**: Tables `record_race`, `record_teamrace`, `record_saves`, `record_points`, and their `_backup` siblings are never read or written — sync does not open them

### Triggers

- [ ] **TRIG-01**: User can start the sync from the website with selectable mode (official, testing, or both)
- [ ] **TRIG-02**: Website shows sync progress and final result (per-file status, byte counts, success/error state)
- [ ] **TRIG-03**: User can start the same sync from the native CLI (`ddnet_control.exe --sync-types-official`, `--sync-types-testing`, `--sync-types`)
- [ ] **TRIG-04**: The native executable auto-triggers a testing-only sync after a successful RCON hot-reload map change, without blocking the map change itself

### Safety

- [ ] **SAFE-01**: Local sync state under `%APPDATA%\DDNet\types\.ddnetcontrol-sync-state.json` lets later official syncs skip unchanged upstream files
- [ ] **SAFE-02**: Every downloaded file is written via temp-then-rename so an interrupted run leaves no half-written `.map`
- [ ] **SAFE-03**: Sync never reads or writes `ddnet-cache.sqlite3`
- [ ] **SAFE-04**: Sync writes only under: `types/**`, `storage.cfg` (create or append with `.bak`), and `record_maps` rows (INSERT OR IGNORE only)
- [ ] **SAFE-05**: Sync never touches `maps/`, `downloadedmaps/`, or any user-uploaded custom maps
- [ ] **SAFE-06**: The auto-trigger (TRIG-04) coalesces map changes within a short window into a single sync run (debounce, no thrash)

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
| SYNC-01 | Phase 1 | Pending |
| SYNC-02 | Phase 1 | Pending |
| SYNC-03 | Phase 1 | Pending |
| SYNC-04 | Phase 1 | Pending |
| TEST-01 | Phase 1 | Pending |
| TEST-02 | Phase 1 | Pending |
| TEST-03 | Phase 1 | Pending |
| CFG-01 | Phase 2 | Pending |
| CFG-02 | Phase 2 | Pending |
| CFG-03 | Phase 2 | Pending |
| CFG-04 | Phase 2 | Pending |
| DB-01 | Phase 2 | Pending |
| DB-02 | Phase 2 | Pending |
| DB-03 | Phase 2 | Pending |
| DB-04 | Phase 2 | Pending |
| TRIG-01 | Phase 3 | Pending |
| TRIG-02 | Phase 3 | Pending |
| TRIG-03 | Phase 4 | Pending |
| TRIG-04 | Phase 4 | Pending |
| SAFE-01 | Phase 1 | Pending |
| SAFE-02 | Phase 1 | Pending |
| SAFE-03 | Phase 1 | Pending |
| SAFE-04 | Phase 2 | Pending |
| SAFE-05 | Phase 1 | Pending |
| SAFE-06 | Phase 4 | Pending |

**Coverage:**
- v1.0 requirements: 25 total
- Mapped to phases: 25 ✓
- Unmapped: 0 ✓

---
*Requirements defined: 2026-05-12 — fresh start after archiving legacy v1.0*
