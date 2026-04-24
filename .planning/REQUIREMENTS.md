# Requirements: DDNet Control

**Defined:** 2026-04-24
**Core Value:** Move the right DDNet maps into the right local folders quickly and safely, without manual copy work or accidental map loss.

## v1 Requirements

### Official Type Sync

- [ ] **SYNC-01**: User can sync the upstream `ddnet-maps/types/` tree into `C:\Users\rust-\AppData\Roaming\DDNet\types`
- [ ] **SYNC-02**: The official type sync preserves upstream relative paths under `types/`
- [ ] **SYNC-03**: The official type sync only downloads files that are new or changed upstream since the last successful sync
- [ ] **SYNC-04**: The official type sync leaves `storage.cfg` untouched

### Testing Map Sync

- [ ] **TEST-01**: User can refresh testing maps from `https://twdata.pati.ga/maplists/ddnet-testing.json` into `C:\Users\rust-\AppData\Roaming\DDNet\types\testingmaps`
- [ ] **TEST-02**: The testing map sync replaces the contents of `testingmaps` from the current remote feed in one run
- [ ] **TEST-03**: The testing map sync validates the remote map URLs before writing files locally

### Triggers

- [ ] **TRIG-01**: User can start the sync flow from the website
- [ ] **TRIG-02**: User can see sync progress and final results from the website
- [ ] **TRIG-03**: User can start the same sync flow from the native/CLI entry point

### Sync State and Safety

- [ ] **SAFE-01**: The sync flow stores local state so later official syncs can skip unchanged upstream files
- [ ] **SAFE-02**: The sync flow reports errors without leaving partial writes in an inconsistent state
- [ ] **SAFE-03**: The sync flow does not modify `ddnet-cache.sqlite3` or `ddnet-server.sqlite`
- [ ] **SAFE-04**: The sync flow writes only under `C:\Users\rust-\AppData\Roaming\DDNet\types`

## v2 Requirements

### Runtime Integration

- **RUNT-01**: User can trigger sync directly from an in-game workflow without manually launching an external executable
- **RUNT-02**: User can schedule background syncs automatically on a cadence

## Out of Scope

| Feature | Reason |
|---------|--------|
| Re-downloading the entire official `types/` tree on every sync | Explicitly rejected by the milestone goal because the upstream set is large and rarely changes |
| Rebuilding or mutating DDNet SQLite record databases during sync | Inspected database schemas are unrelated to sync state and should not be changed without a proven need |
| Editing `storage.cfg` | The live DDNet folder does not currently have one, and the sync flow does not need it |
| Embedded sync command inside the DDNet client itself | Not possible to guarantee from this repo alone without a separate client-side execution path |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| SYNC-01 | Phase 4 | Pending |
| SYNC-02 | Phase 4 | Pending |
| SYNC-03 | Phase 4 | Pending |
| SYNC-04 | Phase 4 | Pending |
| TEST-01 | Phase 5 | Pending |
| TEST-02 | Phase 5 | Pending |
| TEST-03 | Phase 5 | Pending |
| SAFE-01 | Phase 4 | Pending |
| SAFE-02 | Phase 4 | Pending |
| SAFE-03 | Phase 4 | Pending |
| SAFE-04 | Phase 4 | Pending |
| TRIG-01 | Phase 5 | Pending |
| TRIG-02 | Phase 5 | Pending |
| TRIG-03 | Phase 6 | Pending |

**Coverage:**
- v1 requirements: 14 total
- Mapped to phases: 14
- Unmapped: 0 ✓

---
*Requirements defined: 2026-04-24*
*Last updated: 2026-04-24 after planning milestone gap-closure phases*
