# Roadmap: DDNet Control Milestone v1.0 Map Type Auto Sync

## Summary

This milestone adds an end-to-end sync flow for official type maps and testing maps. The implementation is split into three phases so the shared sync engine lands first, then the website trigger, then the native/CLI trigger and final verification.

## Phases

| # | Phase | Goal | Requirements | Success Criteria |
|---|-------|------|--------------|------------------|
| 1 | Build Sync Engine | Create the shared sync logic, local manifest/state, and safe filesystem writes for official and testing sources | SYNC-01, SYNC-02, SYNC-03, SYNC-04, TEST-01, TEST-02, TEST-03, SAFE-01, SAFE-02, SAFE-03, SAFE-04 | 4 |
| 2 | Add Website Trigger | Expose sync start and status through the Python web server and browser UI | TRIG-01, TRIG-02 | 3 |
| 3 | Add Native Trigger and Verify | Add a native/CLI entry point for the same sync logic and verify the milestone behavior | TRIG-03 | 3 |

## Phase Details

### Phase 1: Build Sync Engine

**Goal:** Implement a shared sync engine that can mirror the upstream official `types/` tree incrementally and refresh testing maps safely.

**Requirements:** `SYNC-01`, `SYNC-02`, `SYNC-03`, `SYNC-04`, `TEST-01`, `TEST-02`, `TEST-03`, `SAFE-01`, `SAFE-02`, `SAFE-03`, `SAFE-04`

**Success criteria:**
1. A shared sync module can fetch the upstream official `types/` tree and decide which files are unchanged versus new/updated.
2. Official sync preserves relative paths under `C:\Users\rust-\AppData\Roaming\DDNet\types`.
3. Testing sync can refresh `types\testingmaps` from the JSON feed in one run with safe temporary writes.
4. Sync state is stored locally without mutating `ddnet-cache.sqlite3` or `ddnet-server.sqlite`.

### Phase 2: Add Website Trigger

**Goal:** Let the existing website start sync jobs and show sync results.

**Requirements:** `TRIG-01`, `TRIG-02`

**Success criteria:**
1. The web server exposes endpoints to start a sync job and fetch current sync status.
2. The browser UI has controls for official sync, testing sync, and combined sync.
3. The website shows running status, success summaries, and errors clearly.

### Phase 3: Add Native Trigger and Verify

**Goal:** Let the native executable trigger the same sync flow and verify the milestone behavior.

**Requirements:** `TRIG-03`

**Success criteria:**
1. `ddnet_control.exe` accepts a sync-related CLI flag and routes it to the shared sync flow.
2. The native trigger returns a meaningful success or failure result and logs it.
3. The milestone is verified with targeted sync runs against the live DDNet folder.

## Current Execution Order

1. Phase 1: Build Sync Engine
2. Phase 2: Add Website Trigger
3. Phase 3: Add Native Trigger and Verify

---
*Roadmap created: 2026-04-24 for milestone v1.0 Map Type Auto Sync*
