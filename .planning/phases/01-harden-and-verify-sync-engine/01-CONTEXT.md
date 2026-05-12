# Phase 1: Harden and Verify Sync Engine - Context

**Gathered:** 2026-05-13
**Status:** Ready for planning

<domain>
## Phase Boundary

Prove the existing `tools/map_sync.py` sync engine actually works end-to-end and hardens the safety rails the legacy audit flagged. Covers:

- A real full official sync against the live upstream GitHub tree, populating the local `types/` folder and the `official.files` manifest in `.ddnetcontrol-sync-state.json` for the first time.
- A second-run incremental check proving unchanged files are skipped (0 bytes downloaded).
- An interrupt+resume test proving no half-written `.map` files are ever visible.
- A write-boundary audit proving the run touched only `types/**` (no writes under `maps/`, no modification of DBs).
- Capture of per-phase `SUMMARY.md`, `VERIFICATION.md`, `VALIDATION.md` artifacts so the milestone audit gate passes.

Out of this phase: server visibility (storage.cfg + record_maps — Phase 2), website evidence (Phase 3), native CLI auto-trigger (Phase 4).

</domain>

<decisions>
## Implementation Decisions

### Execution driver
- **D-01:** Run the live full official sync via `python tools/map_sync.py --mode official` using system Python (the repo venv launcher is known broken per legacy audit note); log stdout/stderr to a phase-scoped log under `.planning/phases/01-*/evidence/`.
- **D-02:** Do not modify `sync_official_types` logic beyond what SAFE fixes below require. This phase verifies, not rewrites.

### Safety rail hardening
- **D-03:** `SAFE-02` (atomicity): `stream_download` already uses temp-then-rename. Add a pre-sync audit test that kills the process mid-download (SIGTERM on POSIX / terminate on Windows) and confirms the partial temp file is cleaned or ignored by the next run.
- **D-04:** `SAFE-03` (no DB touch): add an assertion test that takes SHA256 of both `ddnet-server.sqlite` and `ddnet-cache.sqlite3` before and after a sync run; failure if either hash changes.
- **D-05:** `SAFE-05` (no writes to maps/): snapshot `maps/` directory listing + mtimes before sync, diff after, fail if any file changed.
- **D-06:** `TEST-03` (URL validation): the current code only validates on download failure (exception). Add an upfront HEAD (or short GET) per testing URL with a 4xx/5xx threshold; skip a map entirely if its URL is unreachable, log the skip, continue with the rest.

### Incremental semantics proof
- **D-07:** After the full sync completes, run the sync a second time with no upstream change; assert summary reports `skipped == len(manifest)`, `created == 0`, `updated == 0`, `downloaded_bytes == 0`.
- **D-08:** Manifest on disk must be non-empty after first run: `official.files` must contain ≈2412 entries keyed by relative path.

### Evidence format
- **D-09:** Record each verification assertion as a row in `01-VERIFICATION.md` with `id | must-have | actual | pass/fail | evidence-path` columns so the milestone audit can consume it mechanically.
- **D-10:** Preserve the raw summary JSON from each sync run under `.planning/phases/01-*/evidence/` (full-sync.json, incremental.json, interrupted.json).

### Claude's Discretion
- How to implement the kill-mid-sync harness (signal, timer-based, or manual mark). Cross-platform subprocess handling is fiddly on Windows.
- Whether to use `hashlib.sha256` directly or a helper for the DB-untouched check.
- Exact log format for the in-phase run logs (one-line JSON-per-event vs human text). Default to text unless automation demands otherwise.

</decisions>

<specifics>
## Specific Ideas

- The legacy attempt only ran the official sync in `--dry-run` mode against the 1.08 GB tree. This phase runs the REAL download for the first time. Expect it to take 20-60 minutes depending on network.
- Per the milestone audit, the `.ddnetcontrol-sync-state.json` file currently shows `official.files: {}` even though dry-run completed — this is expected for dry-run. The post-phase assertion is that it becomes populated.
- Keep DDNet server closed during the sync run (it doesn't need to be, but it eliminates any chance of misattributed writes in the audit).

</specifics>

<canonical_refs>
## Canonical References

### Sync engine
- `tools/map_sync.py` — engine under test; read especially `sync_official_types()` and `stream_download()`
- `.planning/archive/v1.0-legacy/v1.0-MILESTONE-AUDIT.md` — the gaps this phase closes (all SYNC-*, TEST-*, SAFE-01..05 requirements marked orphaned there)

### Upstream sources
- Tree API: `https://api.github.com/repos/ddnet/ddnet-maps/git/trees/master?recursive=1`
- Raw blob base: `https://raw.githubusercontent.com/ddnet/ddnet-maps/master/`
- Testing feed: `https://twdata.pati.ga/maplists/ddnet-testing.json`

### Live system targets
- `C:\Users\rust-\AppData\Roaming\DDNet\types\` — sync destination
- `C:\Users\rust-\AppData\Roaming\DDNet\types\.ddnetcontrol-sync-state.json` — manifest to populate
- Backup: `C:\Users\rust-\AppData\Roaming\DDNet\.ddnetcontrol-backup-20260513-020207\` — pre-phase DB snapshot for restore

### Requirements
- `.planning/REQUIREMENTS.md` — SYNC-01..04, TEST-01..03, SAFE-01..03, SAFE-05

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `tools/map_sync.py::sync_ddnet_maps(mode, ddnet_root, dry_run, callback)` — full driver, already takes an optional `ddnet_root` for testing without APPDATA
- `tools/map_sync.py::acquire_lock` / `release_lock` — atomic lock file prevents concurrent runs
- `tools/map_sync.py::stream_download` — already writes temp-then-rename; partial cleanup on exception

### Established Patterns
- snake_case Python, explicit logging callback, no external deps beyond stdlib (urllib + hashlib + shutil)
- Progress via callback-based `emit_progress` with `stage`, `message`, `progress`, `counts` fields

### Integration Points
- Phase 2 will wrap this engine with `storage.cfg` + `record_maps` writes; Phase 3 verifies the web endpoint's use of it; Phase 4 wraps the native CLI invocation
- Any safety-rail changes here are contracts Phase 2-4 depend on

</code_context>

<deferred>
## Deferred Ideas

- Parallel downloads (current code is serial; official sync of 1.08 GB serial will be slow) — would change rate-limit behavior, defer to v1.1
- Retry/backoff on 5xx from GitHub raw CDN — current code bubbles exceptions; deferred unless sync fails in practice during this phase
- Progress percent in the UI callback — already has current/total, UI can compute percent itself

</deferred>

---

*Phase: 01-harden-and-verify-sync-engine*
*Context gathered: 2026-05-13*
