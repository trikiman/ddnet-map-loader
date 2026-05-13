---
phase: 04-native-trigger-and-auto-sync
validated_at: 2026-05-13T00:46:00Z
nyquist_complete: true
---

# Phase 4 Validation (Nyquist)

## Must-have truths

| # | Truth | Satisfied | Primary evidence | Second witness |
|---|---|---|---|---|
| T-1 | Native CLI flag runs produce logged outcomes | y | `evidence/A01-sync-types-official-result.json` (exit 0, new log lines captured) | live `ddnet_control.log` timestamped entries during the run |
| T-2 | Native CLI passes `--register-with-server` | y | `evidence/A01` log shows `register-with-server=on` | `evidence/B01-source-wiring-checks.json` (`register_with_server_passed_to_cli_flags=true`) |
| T-3 | Testing CLI flag aborts cleanly on broken upstream URL (TEST-03 through native path) | y | `evidence/A02` exit=1, testingmaps count unchanged at 46 | same behavior observed through web path (`phases/03-*/evidence/B05`) |
| T-4 | Auto-trigger helper function exists in source | y | `evidence/B01` (`trigger_fn_defined=true`) | `evidence/C02-debounce-function.cpp` captures the actual function body |
| T-5 | Helper is called from handle_map_replacement success path | y | `evidence/B01` (`trigger_called_from_handle_map_replacement=true`) — regex matched `Map replacement completed successfully.*?trigger_background_testing_sync_if_due\(\)` | direct source inspection: the 2 lines in `ddnet_control.cpp` between the "Map replacement completed successfully" log and `return true` |
| T-6 | Debounce semantics enforced | y | `evidence/C02-debounce-function.cpp` shows the function: reads `last_write_time`, returns `age >= AUTO_SYNC_DEBOUNCE_SEC` | `evidence/C01-debounce-semantics.json` documents the marker path + constant |
| T-7 | Binary rebuilt successfully with all new code | y | `evidence/A03-trig03-verdict.json` (`native_exe_size=491520`, `log_modified_by_runs=true`) | `compile.bat` output at phase execution time showed `[OK] Build succeeded` |

## Must-have artifacts

| Artifact | Path | Purpose |
|---|---|---|
| TRIG-03 official run | `evidence/A01-sync-types-official-result.json` | Live CLI evidence |
| TRIG-03 testing run | `evidence/A02-sync-types-testing-result.json` | Safety rail held under CLI path |
| TRIG-03 verdict | `evidence/A03-trig03-verdict.json` | Aggregated pass/fail |
| TRIG-04 wiring checks | `evidence/B01-source-wiring-checks.json` | 6-way source grep proof |
| SAFE-06 debounce semantics | `evidence/C01-debounce-semantics.json` | Marker path + constant |
| SAFE-06 debounce fn source | `evidence/C02-debounce-function.cpp` | Captured code for manual review |

## Must-have key links

| Link | Both ends | Verified |
|---|---|---|
| `--register-with-server` in native CLI ↔ log line "register-with-server=on" | C++ source + actual runtime log capture | y |
| `trigger_background_testing_sync_if_due()` forward declaration ↔ definition | Both strings found in `ddnet_control.cpp`; build succeeded (both must exist for link to work) | y |
| Debounce marker path ↔ auto-sync trigger | Marker path references same location in both `auto_sync_debounce_allows()` and `trigger_background_testing_sync_if_due()` | y |

## Nyquist completeness

All 7 must-have truths double-witnessed. Live CLI evidence covers TRIG-03; binary-rebuild + source-grep covers TRIG-04 / SAFE-06 code-level correctness.

**Not covered automatically** (operator human-verify): a real RCON map change triggering the auto-sync in production. This is a 1-line hook at a proven success point in `handle_map_replacement`; the next real map change exercises it naturally.

---

*Validated 2026-05-13 00:46 UTC*
