# Roadmap: DDNet Control Milestone v1.0 Map Type Auto Sync

## In Plain Words

Four phases, each one a clean slice of work with test evidence at the end:

| Phase | What ships | Why |
|---|---|---|
| **1. Harden and verify sync** | The existing `tools/map_sync.py` gets exercised end-to-end: a real full official download, a re-run to prove incremental skipping works, an interrupt+resume test, and a check that nothing outside `types/` got touched. | The legacy v1.0 shipped code but never actually ran a full sync, so we have no evidence it works. Fix that first. |
| **2. Server visibility: `storage.cfg` + `record_maps`** | Sync learns to install the one-line `storage.cfg` fix, and to register new maps in `record_maps` safely (add-only, never touch existing). After this phase your server can actually load every synced map. | Without these two writes, the sync is cosmetic — the server doesn't know those maps exist. |
| **3. Website button verified** | Click the button, see progress, see success or error. Captured as screenshots/logs the milestone audit can sign off. | Legacy v1.0 had the UI code but never captured browser-level evidence. |
| **4. Native CLI + auto-sync on map change + re-audit** | `ddnet_control.exe --sync-types*` flags verified, testing-sync auto-fires after RCON map switches (debounced), milestone audit re-run and passes clean. | Completes the loop and produces the audit-passing artifacts. |

## Phases Summary

| # | Phase | Goal | Requirements | Success Criteria |
|---|-------|------|--------------|------------------|
| 1 | Harden and Verify Sync Engine | Verify the existing sync engine actually executes a full official sync end-to-end, harden safety rails, capture the missing audit evidence | SYNC-01, SYNC-02, SYNC-03, SYNC-04, TEST-01, TEST-02, TEST-03, SAFE-01, SAFE-02, SAFE-03, SAFE-05 | 4 |
| 2 | Server Visibility — `storage.cfg` and `record_maps` | Make synced maps actually loadable by the local DDNet server: install the one-line `storage.cfg` fix and register new maps in `record_maps` safely | CFG-01, CFG-02, CFG-03, CFG-04, DB-01, DB-02, DB-03, DB-04, SAFE-04 | 4 |
| 3 | Verify Website Trigger and UI | Verify the website sync flow end-to-end including browser-visible status states against the real backend | TRIG-01, TRIG-02 | 3 |
| 4 | Native Trigger, Auto-Sync on Map Change, and Re-Audit | Verify the native CLI flags, add RCON-map-change auto-trigger with debounce, re-run the milestone audit | TRIG-03, TRIG-04, SAFE-06 | 4 |

## Phase Details

### Phase 1: Harden and Verify Sync Engine

**Goal:** Execute a real full official sync, confirm incremental semantics on a second run, verify every safety rail, and capture the per-phase artifacts the legacy audit said were missing.

**Requirements:** `SYNC-01`, `SYNC-02`, `SYNC-03`, `SYNC-04`, `TEST-01`, `TEST-02`, `TEST-03`, `SAFE-01`, `SAFE-02`, `SAFE-03`, `SAFE-05`

**Canonical refs:**
- `tools/map_sync.py` — existing sync engine (carried from legacy)
- `.planning/archive/v1.0-legacy/v1.0-MILESTONE-AUDIT.md` — what was missing before
- Upstream tree API: `https://api.github.com/repos/ddnet/ddnet-maps/git/trees/master?recursive=1`
- Testing feed: `https://twdata.pati.ga/maplists/ddnet-testing.json`

**Success criteria:**
1. A full official sync completes end-to-end against the live upstream and populates both `%APPDATA%\DDNet\types\<category>\**` and the `official.files` manifest in `.ddnetcontrol-sync-state.json`.
2. A second run with no upstream changes reports `skipped = <full count>`, `created = 0`, `updated = 0`, `downloaded_bytes = 0` (proves incremental semantics).
3. An interrupt-then-resume test leaves no half-written `.map` files (proves temp-then-rename atomicity) and the next run correctly fills in the interrupted files.
4. A write-boundary audit confirms the run touched only `types/**`; no modification time changed under `maps/`, `downloadedmaps/`, `ddnet-cache.sqlite3`, or `ddnet-server.sqlite`.

### Phase 2: Server Visibility — `storage.cfg` and `record_maps`

**Goal:** Teach the sync engine to make its own output actually usable by the local DDNet server, via the one-line `storage.cfg` fix and safe `record_maps` registration.

**Requirements:** `CFG-01`, `CFG-02`, `CFG-03`, `CFG-04`, `DB-01`, `DB-02`, `DB-03`, `DB-04`, `SAFE-04`

**Canonical refs:**
- Official upstream `storage.cfg`: `https://raw.githubusercontent.com/ddnet/ddnet-maps/master/storage.cfg`
- DDNet engine storage convention: `add_path <dir>` resolves recursively for map lookup
- Legacy `add_maps.ps1` in `%APPDATA%\DDNet\` — the anti-pattern (DELETE + INSERT wiped metadata) that DB-02 / DB-03 explicitly prevent

**Success criteria:**
1. `storage.cfg` handling covers all three cases correctly: absent (create with defaults + the line), present-without-line (append + `.bak`), present-with-line (no-op).
2. After sync, any new map in `types/` has a row in `record_maps`; existing rows keep every column byte-identical to what they were before the run.
3. SQL trace (or audit of the sync engine's statements) shows only `INSERT OR IGNORE` against `record_maps` — zero `DELETE`, zero `UPDATE`, zero reads/writes against any other record table.
4. End-to-end check: with a fresh `storage.cfg` and fresh row, `ddnet_control.exe` can run `sv_map "<a-known-synced-name>"` and the server loads the map successfully.

### Phase 3: Verify Website Trigger and UI

**Goal:** Confirm the existing website sync path works end-to-end from browser click to visible success/error state, and produce the browser-level evidence the legacy audit said was missing.

**Requirements:** `TRIG-01`, `TRIG-02`

**Canonical refs:**
- `web/server.py` — existing `/sync-types` (POST) and `/sync-status` (GET) endpoints
- `web/index.html`, `web/script.js` — existing sync controls and status polling

**Success criteria:**
1. From the browser, the user can pick mode (official, testing, all) and start a sync that reaches the Python server and invokes the sync engine with the chosen mode.
2. The browser UI transitions through `queued → running → success` (or `→ error`) states as reflected in `/sync-status`, with per-file progress visible while the job runs.
3. On error, the browser surfaces the error message and leaves the previous sync state intact (no partial manifest drift).

### Phase 4: Native Trigger, Auto-Sync on Map Change, and Re-Audit

**Goal:** Verify the existing native CLI flags, add the RCON-map-change auto-trigger with debounce, and re-run the milestone audit to confirm all gaps close.

**Requirements:** `TRIG-03`, `TRIG-04`, `SAFE-06`

**Canonical refs:**
- `ddnet_control.cpp` — existing `--sync-types`, `--sync-types-official`, `--sync-types-testing` flags and RCON `sv_map` hot-reload logic

**Success criteria:**
1. `ddnet_control.exe --sync-types-testing`, `--sync-types-official`, and `--sync-types` each complete successfully against the live DDNet folder and log the outcome to `ddnet_control.log`.
2. After a successful RCON hot-reload map change, the native executable fires a testing-only sync within a few seconds, without blocking the map change itself.
3. Rapid-fire three map changes within a short window produces at most one sync run (debounce proof for SAFE-06).
4. A re-run of the milestone audit (`/gsd-audit-milestone`) returns clean — every requirement traced to a phase with SUMMARY, VERIFICATION, and VALIDATION evidence.

## Current Execution Order

1. Phase 1: Harden and Verify Sync Engine
2. Phase 2: Server Visibility — `storage.cfg` and `record_maps`
3. Phase 3: Verify Website Trigger and UI
4. Phase 4: Native Trigger, Auto-Sync on Map Change, and Re-Audit

## Requirements Coverage

| Requirement | Phase |
|-------------|-------|
| SYNC-01 | Phase 1 |
| SYNC-02 | Phase 1 |
| SYNC-03 | Phase 1 |
| SYNC-04 | Phase 1 |
| TEST-01 | Phase 1 |
| TEST-02 | Phase 1 |
| TEST-03 | Phase 1 |
| CFG-01 | Phase 2 |
| CFG-02 | Phase 2 |
| CFG-03 | Phase 2 |
| CFG-04 | Phase 2 |
| DB-01 | Phase 2 |
| DB-02 | Phase 2 |
| DB-03 | Phase 2 |
| DB-04 | Phase 2 |
| TRIG-01 | Phase 3 |
| TRIG-02 | Phase 3 |
| TRIG-03 | Phase 4 |
| TRIG-04 | Phase 4 |
| SAFE-01 | Phase 1 |
| SAFE-02 | Phase 1 |
| SAFE-03 | Phase 1 |
| SAFE-04 | Phase 2 |
| SAFE-05 | Phase 1 |
| SAFE-06 | Phase 4 |

**Coverage:** 25 of 25 requirements mapped (100%)

---
*Roadmap created: 2026-05-12 for fresh-start milestone v1.0 Map Type Auto Sync*
