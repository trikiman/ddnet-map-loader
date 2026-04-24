# Roadmap: DDNet Control Milestone v1.0 Map Type Auto Sync

## Summary

This milestone adds an end-to-end sync flow for official type maps and testing maps. The implementation is split into three phases so the shared sync engine lands first, then the website trigger, then the native/CLI trigger and final verification.

## Phases

| # | Phase | Goal | Requirements | Success Criteria |
|---|-------|------|--------------|------------------|
| 1 | Build Sync Engine | Create the shared sync logic, local manifest/state, and safe filesystem writes for official and testing sources | SYNC-01, SYNC-02, SYNC-03, SYNC-04, TEST-01, TEST-02, TEST-03, SAFE-01, SAFE-02, SAFE-03, SAFE-04 | 4 |
| 2 | Add Website Trigger | Expose sync start and status through the Python web server and browser UI | TRIG-01, TRIG-02 | 3 |
| 3 | Add Native Trigger and Verify | Add a native/CLI entry point for the same sync logic and verify the milestone behavior | TRIG-03 | 3 |

## Gap Closure Phases

These phases close the audit gaps from `.planning/v1.0-MILESTONE-AUDIT.md`. They supersede the original traceability assignments for milestone completion because the original phases were implemented without GSD execution artifacts.

| # | Phase | Goal | Requirements | Success Criteria |
|---|-------|------|--------------|------------------|
| 4 | Complete Official Types Sync | Run and verify the full upstream `types/` sync so the local DDNet folder actually contains the official type directories and files | SYNC-01, SYNC-02, SYNC-03, SYNC-04, SAFE-01, SAFE-02, SAFE-03, SAFE-04 | 4 |
| 5 | Verify Website Sync Flow | Verify the website-triggered sync end to end and capture the missing audit evidence for the browser path and testing-map path | TEST-01, TEST-02, TEST-03, TRIG-01, TRIG-02 | 4 |
| 6 | Verify Native Sync and Re-Audit | Verify the native sync trigger end to end, capture the remaining evidence, and re-run milestone audit | TRIG-03 | 4 |

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

### Phase 4: Complete Official Types Sync

**Goal:** Execute the full official types sync and verify that the local `C:\Users\rust-\AppData\Roaming\DDNet\types` tree contains the upstream type directories and files rather than only `testingmaps`.

**Requirements:** `SYNC-01`, `SYNC-02`, `SYNC-03`, `SYNC-04`, `SAFE-01`, `SAFE-02`, `SAFE-03`, `SAFE-04`

**Gap Closure:** Closes the audit requirement gaps for official sync plus the flow gap stating that the official full sync was never milestone-verified.

**Success criteria:**
1. Local `types\` contains the upstream top-level type directories such as `brutal`, `dummy`, `solo`, and the related subtree content after sync.
2. Incremental sync state for official files is persisted in `.ddnetcontrol-sync-state.json` with non-empty `official.files`.
3. The sync is verified to avoid writing outside `C:\Users\rust-\AppData\Roaming\DDNet\types` and to leave unrelated SQLite files untouched.
4. Phase artifacts document the full official sync result and evidence.

### Phase 5: Verify Website Sync Flow

**Goal:** Verify the website sync path end to end, including testing-map refresh and browser-visible status reporting.

**Requirements:** `TEST-01`, `TEST-02`, `TEST-03`, `TRIG-01`, `TRIG-02`

**Gap Closure:** Closes the audit gaps for website integration, testing-map verification, and the missing browser-level flow evidence.

**Success criteria:**
1. The website can trigger `testing`, `official`, and `all` sync modes through `/sync-types`.
2. Browser-visible status updates correctly reflect queued, running, success, and failure states from `/sync-status`.
3. Testing map refresh is verified against the remote JSON feed and local `types\testingmaps`.
4. Phase artifacts capture browser/UI evidence, not just server-side code presence.

### Phase 6: Verify Native Sync and Re-Audit

**Goal:** Verify the native CLI trigger and close the remaining audit/documentation gaps so the milestone can pass re-audit.

**Requirements:** `TRIG-03`

**Gap Closure:** Closes the remaining native-trigger gap, integration gap, and milestone-level audit evidence gap.

**Success criteria:**
1. `ddnet_control.exe --sync-types-testing`, `--sync-types-official`, and `--sync-types` are verified with logged outcomes.
2. Native sync fallback behavior is verified on this machine where the repo venv launcher is broken.
3. Required `SUMMARY.md`, `VERIFICATION.md`, and `VALIDATION.md` artifacts exist for the gap-closure phases.
4. `$gsd-audit-milestone` is rerun and the remaining milestone blockers are resolved or narrowed explicitly.

## Current Execution Order

1. Phase 4: Complete Official Types Sync
2. Phase 5: Verify Website Sync Flow
3. Phase 6: Verify Native Sync and Re-Audit

---
*Roadmap created: 2026-04-24 for milestone v1.0 Map Type Auto Sync*
