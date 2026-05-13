# Phase 3: Verify Website Trigger and UI - Context

**Gathered:** 2026-05-13
**Status:** Ready for planning (retroactively documented alongside execution)

<domain>
## Phase Boundary

Verify the existing `web/server.py` + `web/script.js` sync flow works end-to-end from HTTP POST to visible terminal state. The code is already in place from the legacy attempt; Phase 3 adds:

1. Wire `register_with_server=True` into `web/server.py::run_sync_job` so the website trigger invokes Phase 2's safety-rail-protected DB writes after sync.
2. Add a headless launch mode (`DDNETCONTROL_NO_TRAY=1`) so automated verification can spawn the server without the tray-icon blocking loop.
3. Drive the full state machine: idle → queued → running → success | error.
4. Exercise concurrency lock (second POST while first is running → 409).
5. Exercise invalid-mode rejection (400).

Out of this phase: native CLI + RCON auto-trigger (Phase 4), browser screenshot evidence (deferred — the JSON state captures are equivalent-evidence for automated audit; real browser screenshots are a manual checkpoint step).

</domain>

<decisions>
## Implementation Decisions

- **D-01:** Use HTTP-level verification (POST/GET + JSON state machine) rather than browser DOM automation. The JSON status is what the UI renders from; covering it covers the UI behavior. Manual browser screenshot is a checkpoint item, not an automated gate.
- **D-02:** Drive Phase A via `mode=official` (idempotent 0-byte rerun proven in Phase 1 — fast, repeatable, side-effect-free).
- **D-03:** Drive Phase B via `mode=testing` — upstream has a live broken URL (`Evening_Mist.map` 404 at time of execution), which is a **production exercise** of TEST-03 through the full UI stack.
- **D-04:** Concurrency probe: fire two POSTs with 100 ms delay; expect first `202 Accepted`, second `409 Conflict` while first still running.
- **D-05:** Invalid-mode probe: POST with `mode=bogus`; expect `400 Bad Request` with a JSON error body.
- **D-06:** Add a `DDNETCONTROL_NO_TRAY=1` env-var escape hatch in `web/server.py`'s main block. No tray icon, no console-hide, no webbrowser.open. Headless, foreground HTTPServer. Used by the verify harness; harmless for all other uses.
- **D-07:** Wire Phase 2 into the web trigger: `run_sync_job` calls `sync_ddnet_maps(mode=mode, callback=on_progress, register_with_server=True)`. The `summary.server_register` field surfaces on `/sync-status` for the UI to render.

### Claude's Discretion
- Exact UI copy for "server_register" summary rendering — the existing script.js will surface it via the generic summary renderer; polish deferred.
- Whether to add a browser screenshot sidecar. Deferred.

</decisions>

<specifics>
## Specific Ideas

- The testing feed is **live**, so the error path in Phase B is a genuine production test — if all upstream URLs are reachable on a future run, Phase B's assertions need to loosen. The verdict script should check either "success=true" OR "success=false AND testingmaps intact AND error mentions unreachable" — but that's future-proofing the verify script, not the phase proof.
- The legacy `/sync-types` endpoint already supports `mode=all|official|testing` and `/sync-status` polling every 3 s in script.js — no UI rewrite needed.

</specifics>

<canonical_refs>
## Canonical References

- `web/server.py` — existing sync endpoints and job orchestration (lines ~33-135 for sync state; ~400-820 for endpoints)
- `web/script.js` — UI polling + state rendering (lines ~31-140)
- `.planning/phases/01-harden-and-verify-sync-engine/01-SUMMARY.md` — Phase 1 stable JSON summary schema
- `.planning/phases/02-server-visibility/02-SUMMARY.md` — Phase 2 `register_with_server` contract

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `web/server.py::start_sync_job` + `run_sync_job` thread wrapper — already thread-safe with `SYNC_STATUS_LOCK`
- `web/server.py::append_sync_log` — rolling log of last 40 messages, already exposed via `/sync-status`
- `web/script.js::renderSyncStatus` — renders any state dict including unknown keys via generic summary path

### Integration Points
- Phase 2's `register_with_server` hook is now called from `run_sync_job`; `summary.server_register` surfaces automatically
- Phase 4 will share the same `sync_ddnet_maps(register_with_server=True)` wiring from the native side

</code_context>

<deferred>
## Deferred Ideas

- Browser-level Chrome DevTools screenshot evidence — JSON state equivalent-evidence is acceptable for automated audit; manual browser visual check is the human-verify checkpoint.
- Proper 4xx rejection for unknown modes — existing code returns 400 `{"error": "Invalid sync mode: bogus"}` which is correct; polish deferred.

</deferred>

---

*Phase: 03-verify-website-trigger*
*Context: retroactive, 2026-05-13*
