# State

## Project Reference

See: `.planning/PROJECT.md` (updated 2026-05-13)
**Session handoff:** `.planning/HANDOFF-2026-05-14.md` ← read this first if continuing

**Core value:** Move the right DDNet maps into the right local folders quickly and safely, without manual copy work, without accidental map loss, and without destructive edits to existing DDNet data.
**Current focus:** Milestone v1.0 SHIPPED. Three production bugs found post-audit and all fixed (commits 602ee30, fca71de, ce3c3e6). Awaiting `/gsd-audit-milestone` re-run with new evidence, or proceed to v1.1.

## Current Position

Phase: All 4 phases COMPLETE + post-audit hardening done
Plan: `.planning/ROADMAP.md`
Status: Live system verified working end-to-end (all 4261 maps load via vote/RCON, zero datafile errors)
Last activity: 2026-05-14 — combined `types/_all/` hardlink dir feature committed (ce3c3e6). Session winding down for handoff.

## Phase Status

| # | Phase | Status | Commit | Requirements |
|---|-------|--------|--------|--------------|
| 1 | Harden and Verify Sync Engine | ✅ PASSED | 9195de8 | SYNC-01..04, TEST-02/03, SAFE-01/02/03/05 (10 PASS, 1 PARTIAL = TEST-01) |
| 2 | Server Visibility — storage.cfg + record_maps | ✅ PASSED + post-audit fixes | d0314df, 602ee30, fca71de, ce3c3e6 | CFG-01..04, DB-01..04, SAFE-04 (all PASS — sv_map now live-verified) |
| 3 | Verify Website Trigger and UI | ✅ PASSED | 82bf6c1 | TRIG-01, TRIG-02 (2 PASS) |
| 4 | Native CLI + RCON Auto-Sync | ✅ PASSED | f217663 | TRIG-03, TRIG-04, SAFE-06 (3 PASS) |

## Milestone Scorecard

- **Requirements closed (PASS or PASS-via-unit): 24 / 25** (CFG-04 reclassified PASS after live econ verification 2026-05-14)
- **Partial (external conditions): 1 / 25** — TEST-01 (live upstream has broken URL, safety rail held in its place; cannot be demo'd until upstream fixes)
- **Failed: 0 / 25**

## Post-Audit Hardening (2026-05-14)

After the v1.0 milestone was marked audit-ready (3ff5b4d), the user found that maps couldn't be voted in production. Three layered bugs were discovered and fixed:

| Commit | Bug | Fix |
|--------|-----|-----|
| `602ee30` | storage.cfg single-line wrong shape; testingmaps wrote to wrong layout; record_maps.Server used category instead of 'DDNet' | Multi-line per-category storage.cfg; testingmaps now under `maps/` subfolder + migration; hardcoded `Server='DDNet'`; opt-in `--repair-server-column` for stale rows |
| `fca71de` | DDNet's storage.cfg lives at `$CURRENTDIR` (Steam install dir, not `%APPDATA%`); `$USERDIR` not expanded as a prefix per upstream `storage.cpp::AddPath()` source | Absolute paths in storage.cfg; `_resolve_server_storage_cfg()` finds the install dir via WMIC + drive probing |
| `ce3c3e6` | DDNet `MAX_PATHS=16` cap dropped fun/event categories | New `types/_all/maps/` combined hardlink dir; single add_path covers all categories. 4212 → 4261 maps in maplist |

Live verification (per Verification.md steering rule):
- Web UI sync triggered via Chrome DevTools MCP — `success=true`
- Server boot log: 4 add_paths total, zero `cannot add path` errors
- econ change_map for 5 maps across categories (oldschool, testingmaps×2, event, fun) — all PASS, zero datafile errors
- `8bit Full Adder` shows full game-state init (switches/zones/tuning) — proves real playability

## Accumulated Context

Milestone v1.0 (Map Type Auto Sync) end-to-end flow:

1. **Sync engine** (`tools/map_sync.py`, Phase 1): pulls upstream official `types/` incrementally (SHA + size manifest), pulls testing maps with TEST-03 URL pre-validation, atomic writes via temp-then-rename, orphan sweep on startup
2. **Server visibility** (`tools/server_register.py`, Phase 2 + post-audit hardening):
   - `rebuild_combined_maps_dir()` hardlinks every map into `types/_all/maps/`
   - `ensure_storage_cfg()` writes one absolute add_path for `_all` (rewrites our own files canonically when content drifts)
   - `register_maps_in_db()` INSERT OR IGNOREs every stem with `Server='DDNet'`
   - VACUUM INTO backup before any DB write; rolling 3-backup retention
3. **Website trigger** (`web/server.py`, Phase 3 + Steam-install resolver): `/sync-types` POST accepts `all`/`official`/`testing`; `/sync-status` GET exposes queued → running → success/error state machine. `_resolve_server_storage_cfg()` finds the running DDNet-Server.exe's storage.cfg via WMIC, falling back to drive probing (newest mtime wins).
4. **Native trigger** (`ddnet_control.cpp`, Phase 4): `--sync-types-*` flags with venv→py-3→python fallback; post-RCON-map-change auto-trigger fires detached testing-only sync; 60 s debounce via `.ddnetcontrol-last-auto-sync` marker.

### Safety rails enforced and verified end-to-end

- `maps/` (1799 files): byte-identical before/after every sync — never written to under any code path
- `downloadedmaps/` (307 files): byte-identical before/after every sync
- `ddnet-cache.sqlite3`: SHA256 unchanged across any sync + DB write
- `ddnet-server.sqlite`: only `record_maps` INSERT OR IGNORE (or opt-in repair UPDATE for our-only rows); all other tables untouched
- Existing user-modified `record_maps` rows byte-identical (Mapper/Points/Stars preserved)
- Testing sync never deletes `testingmaps/` when any URL is unreachable

### Key numbers (post-2026-05-14)

- Upstream: 2468 files, 1.08 GB, tree SHA `14b4b9936f02da830f3ceaddc54f49ceec336cbf`
- Combined dir: 2463 hardlinks under `types/_all/maps/`, near-zero disk overhead
- Server maplist: **4261 maps** (was 4212 before combined-dir feature)
- record_maps: 3447 with `Server='DDNet'`, 6 stale rows for stems no longer synced (left alone)

### Pre-phase backups (recovery paths)

- `.ddnetcontrol-backup-20260513-020207/` — full pre-milestone snapshot (DBs + sync state)
- `.ddnetcontrol-server-backup-*.sqlite` — most-recent VACUUM INTO snapshots (3 retained, rotated)
- `E:\SteamLibrary\steamapps\common\DDraceNetwork\ddnet\storage.cfg.bak` — pre-rewrite snapshot of the active storage.cfg

---
*Last updated: 2026-05-14 after combined-dir feature commit ce3c3e6. Milestone v1.0 SHIPPED + hardened. Read `HANDOFF-2026-05-14.md` for full session-swap context.*
