# Phase 4: Native Trigger + Auto-Sync on Map Change - Context

**Gathered:** 2026-05-13
**Status:** Ready for planning (retroactive)

<domain>
## Phase Boundary

Verify the native CLI sync flags work against the live system, add an auto-trigger that fires a testing-only sync after an RCON map change (debounced), rebuild and smoke-test the executable.

1. **TRIG-03 (existing code)** — verify `ddnet_control.exe --sync-types-testing`, `--sync-types-official`, `--sync-types` produce logged outcomes. Wire `--register-with-server` through so Phase 2 runs from the native path too.
2. **TRIG-04 (new)** — after a successful `handle_map_replacement` (the RCON map change path), fire a detached testing-only sync process. Non-blocking — map change must not stall waiting for the sync.
3. **SAFE-06 (new)** — debounce the auto-trigger via a file marker so rapid-fire map changes within a 60 s window produce at most one sync.

</domain>

<decisions>
## Implementation Decisions

- **D-01:** Auto-trigger fires from `handle_map_replacement` (end of the success branch), not from RCON message handling. Rationale: `handle_map_replacement` is the canonical RCON map-change entry that both upload flow and restore flow funnel through. Hooking it covers both paths with one change.
- **D-02:** Detached process via `CreateProcessW` with `DETACHED_PROCESS | CREATE_NO_WINDOW` — no console pop, no blocking on exit. `CloseHandle(pi.hProcess)` immediately so the OS reaps it when done.
- **D-03:** Debounce marker at `%APPDATA%\DDNet\types\.ddnetcontrol-last-auto-sync`. Check mtime; if age < 60 s, return without spawning. Otherwise touch the marker first then spawn. Single source of truth, survives process restarts.
- **D-04:** Debounce window: 60 seconds. Short enough to feel responsive (map change → new testing maps within a minute), long enough to absorb rapid-fire map switches (CI / testing setup where operator flips through maps).
- **D-05:** Auto-trigger uses `--mode testing --register-with-server`. Testing only (cheap, no GitHub rate-limit risk). Register-with-server so new testing maps automatically get their `record_maps` row via Phase 2.
- **D-06:** Python fallback chain for the auto-trigger's spawned process: same as `run_sync_types_command` — try venv → py -3 → python. Wrap in `cmd.exe /c "A || B || C"` so the first success wins.
- **D-07:** Native CLI path (`run_sync_types_command`) also passes `--register-with-server` now. Matches the website path's behavior (Phase 3 already sets this).
- **D-08:** Cannot automate a full "live RCON map change triggers auto-sync" test from Python without a running DDNet server. So verification uses a hybrid approach: live CLI flag test for TRIG-03 + source-level grep proofs for TRIG-04/SAFE-06 wiring. A real map-change event in normal usage will exercise the full path.

### Claude's Discretion
- Whether to spawn via `CreateProcessW` or `_spawnlp`. CreateProcessW gives explicit DETACHED_PROCESS flag.
- Log level for the auto-trigger fire — INFO ("Auto-sync: background testing sync started") and WARNING for the debounce-skip case.

</decisions>

<specifics>
## Specific Ideas

- `compile.bat` worked on the user's machine at build time (the earlier audit said it had issues; those appear to have been fixed since).
- The venv still fails with exit code 103 (legacy issue); the fallback chain is reached and works.
- `ddnet_control.log` at `%APPDATA%\DDNet\maps\ddnet_control.log` is the canonical log sink for all native runs; TRIG-03 evidence is read from there.

</specifics>

<canonical_refs>
## Canonical References

- `ddnet_control.cpp` — native source. Key symbols: `handle_map_replacement` (line ~1411), `run_sync_types_command` (line ~1233), the new `trigger_background_testing_sync_if_due` / `auto_sync_debounce_allows` / `auto_sync_touch_marker` helpers (new, inserted after `run_sync_types_command`).
- `compile.bat` — build script, works on the user's machine.
- `.planning/phases/01-harden-and-verify-sync-engine/01-SUMMARY.md` — stable CLI contract this phase consumes.
- `.planning/phases/02-server-visibility/02-SUMMARY.md` — `--register-with-server` contract.
- `.planning/phases/03-verify-website-trigger/03-SUMMARY.md` — Phase 3 wired the web path; Phase 4 wires the native path to the same contract.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `run_hidden_process(exe, args, cwd)` — already used by `run_sync_types_command`
- `Logger::log(Logger::INFO, ...)` — the canonical logging sink
- `fs` (alias for `std::filesystem`) already imported

### Integration Points
- `handle_map_replacement` always ends with `Logger::log(..., "Map replacement completed successfully")` before returning true — perfect hook point
- `run_sync_types_command` builds its script args in one place — adding `--register-with-server` is a 1-line change

</code_context>

<deferred>
## Deferred Ideas

- Hook `restore_from_backup` too — currently only `handle_map_replacement` fires the auto-sync. Restore is rare enough that debounce would kick in if it happened right after a regular change; single-hook is simpler and covers the common case.
- Per-mode auto-trigger config (user could say "never auto-trigger" or "auto-trigger for official too"). Deferred to v1.1 RUNT-02.
- Auto-sync runs in detached process, so its completion/failure is invisible to the native executable. Could add a post-completion log that either succeeds or logs warning. Deferred — the sync's own log is the source of truth.

</deferred>

---

*Phase: 04-native-trigger-and-auto-sync*
*Context: retroactive, 2026-05-13*
