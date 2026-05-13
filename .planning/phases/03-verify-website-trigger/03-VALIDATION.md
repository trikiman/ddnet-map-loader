---
phase: 03-verify-website-trigger
validated_at: 2026-05-13T00:31:00Z
nyquist_complete: true
---

# Phase 3 Validation (Nyquist)

## Must-have truths

| # | Truth | Satisfied | Primary evidence | Second witness |
|---|---|---|---|---|
| T-1 | Website can start sync via POST /sync-types | y | `evidence/A02-start-response.json` (HTTP 202, running=true) | `evidence/B02-start-response.json` (different mode, same endpoint, same 202) |
| T-2 | UI status reflects full state machine | y | `evidence/A03-state-transitions.json` (success path transitions queued→official→storage_cfg→record_maps→done) | `evidence/B03-state-transitions.json` (error path transitions queued→testing→error) |
| T-3 | Final success state correctly reports summary | y | `evidence/A04-final-status.json` (success=true, summary.official with byte counts, summary.server_register with Phase 2 data) | `evidence/A05-verdict.json` (explicit `summary_has_official=true`, `summary_has_server_register=true`) |
| T-4 | Final error state correctly reports cause | y | `evidence/B04-final-status.json` (success=false, error field populated, stage=error) | `evidence/B05-verdict.json` (explicit `final_success_is_false=true`, `error_message_mentions_unreachable=true`) |
| T-5 | Safety rail (TEST-03) holds under production UI-triggered flow | y | `evidence/B05-verdict.json` (testingmaps_count_pre=46, testingmaps_count_post=46, testingmaps_intact=true) | raw counts in `evidence/B04-final-status.json` match |
| T-6 | Concurrency lock rejects simultaneous syncs | y | `evidence/C01-concurrency.json` (first_http=202, second_http=409) | second_body captured (running=true, stage=official) |
| T-7 | Invalid mode is rejected cleanly | y | `evidence/D01-invalid-mode.json` (http_code=400, body has error field) | response body `{"error": "Invalid sync mode: bogus"}` is the specific rejection reason |

## Must-have artifacts

| Artifact | Path | Purpose |
|---|---|---|
| Phase A idle / start / transitions / final / verdict | `A01-*.json` through `A05-*.json` | Success path |
| Phase B start / transitions / final / verdict | `B02-*.json` through `B05-*.json` | Error path (TEST-03 live) |
| Phase C concurrency | `C01-concurrency.json` | Lock test |
| Phase D invalid mode | `D01-invalid-mode.json` | Rejection test |

## Must-have key links

| Link | Both ends | Verified |
|---|---|---|
| Phase A POST mode=official ↔ Phase A final summary.official | A02 shows mode=official sent; A04 summary.official present | y |
| Phase 2 wiring ↔ Phase 3 summary.server_register | Phase 2 modified web/server.py run_sync_job to pass register_with_server=True; A04 final_status.summary.server_register is not None | y |
| TEST-03 safety rail ↔ UI error surface | Phase 1 implemented pre-validation; Phase 3 B04 final_status.error contains the same "unreachable" wording; testingmaps unchanged | y |

---

*Validated 2026-05-13 00:31 UTC*
