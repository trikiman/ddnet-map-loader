# Phase 2: Server Visibility — `storage.cfg` and `record_maps` - Context

**Gathered:** 2026-05-13
**Status:** Ready for planning

<domain>
## Phase Boundary

Make the maps that Phase 1 synced into `types/` actually loadable by the local DDNet server. Two writes, both targeted and reversible:

1. **`storage.cfg` install** — if missing, create with `add_path $USERDIR/types` plus the three defaults (`$USERDIR`, `$DATADIR`, `$CURRENTDIR`). If present without the line, append and back up to `storage.cfg.bak`. If already correct, no-op.
2. **`record_maps` registration** — for each map file present in `types/` that does not have a row in `ddnet-server.sqlite -> record_maps`, `INSERT OR IGNORE` a minimal row (`Map=<basename-stem>, Server=<category>, Mapper='Unknown', Points=0, Stars=0`). Never DELETE, never UPDATE, never touch other tables.

Out of this phase: UI wiring (Phase 3), native CLI and RCON auto-trigger (Phase 4). Phase 1 contracts are consumed: writes remain bounded to `types/**` + `storage.cfg` + `record_maps` row inserts.

</domain>

<decisions>
## Implementation Decisions

### `storage.cfg` install logic
- **D-01:** Install path: `%APPDATA%\DDNet\storage.cfg` (same dir as the SQLite files, NOT under `types/`). Use `get_ddnet_root()` from `map_sync`, not a hardcoded string.
- **D-02:** Content when creating anew: exactly four lines:
  ```
  add_path $USERDIR
  add_path $DATADIR
  add_path $CURRENTDIR
  add_path $USERDIR/types
  ```
  Matches DDNet engine conventions (three defaults + the one that gives us recursive `types/` lookup).
- **D-03:** Detection: read the file, strip comments (`#` and `//` anywhere), match the line `add_path $USERDIR/types` with flexible whitespace but case-sensitive (DDNet is case-sensitive on paths). Forward slash required (engine accepts both but we standardize).
- **D-04:** Append flow: if file exists but line missing, read full content, back up to `storage.cfg.bak` (but only if `.bak` doesn't already exist — never overwrite an existing backup), then append `add_path $USERDIR/types\n` and write back atomically (temp-then-rename).
- **D-05:** No-op flow: if the exact line already present (after comment strip + whitespace normalize), log and return without writing.

### `record_maps` registration logic
- **D-06:** Write path: `%APPDATA%\DDNet\ddnet-server.sqlite` → table `record_maps`. Schema (confirmed via inspection):
  ```sql
  CREATE TABLE record_maps (
    Map VARCHAR(128) COLLATE BINARY NOT NULL,
    Server VARCHAR(32) COLLATE BINARY NOT NULL,
    Mapper VARCHAR(128) COLLATE BINARY NOT NULL,
    Points INT DEFAULT 0,
    Stars INT DEFAULT 0,
    Timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (Map)
  )
  ```
  Primary key is `Map` alone — so `INSERT OR IGNORE` with an existing `Map` string is the natural no-touch-existing operation.
- **D-07:** Map name key: the `Map` column matches what DDNet's server uses when loading a map. Inspection of DDNet's `IStorage` convention: when `storage.cfg` adds `types`, the server resolves `sv_map "Kobra 4"` by scanning added paths for `Kobra 4.map`. So the `Map` value is the **stem** (basename without `.map`), matching the upstream filename exactly.
- **D-08:** Server value: the category (e.g., `novice`, `brutal`, `solo`). Derived from the first path segment under `types/` in the sync manifest. For `types/novice/Kobra 4.map` → `Server = "novice"`. For `types/testingmaps/Foo.map` → `Server = "testing"` (explicit alias). For anything under `types/ddmax.easy/` etc. the whole category name is preserved.
- **D-09:** Mapper: `'Unknown'` for sync-added rows. Never overwrites an existing Mapper. If a user has manually set Mapper via another tool, we preserve it (INSERT OR IGNORE).
- **D-10:** Points/Stars: default to 0. The legacy `add_maps.ps1` behavior was this, but then it DELETEd everything first — which is the bug we're fixing. With INSERT OR IGNORE, existing Points/Stars stay.
- **D-11:** Concurrency: open the SQLite connection with `PRAGMA busy_timeout = 5000` and write inside a single transaction. If the server is running and holds a write lock, we retry briefly then fail with a clear message (never block indefinitely).
- **D-12:** Where this code lives: new module `tools/server_register.py` with pure functions `ensure_storage_cfg(ddnet_root)` and `register_maps_in_db(ddnet_root, manifest)` — callable from `sync_ddnet_maps` as a post-sync step. Keep `map_sync.py` focused on pulling files; the server-visibility concerns live one layer up.

### Integration with existing sync flow
- **D-13:** `sync_ddnet_maps` grows a new optional parameter `register_with_server: bool = True` — when true, after a successful official or testing sync it calls `ensure_storage_cfg` then `register_maps_in_db` using the freshly-written state. Set false in unit tests and for the Phase 1 dry-runs (already done).
- **D-14:** Summary JSON gains two top-level fields: `storage_cfg` (with `action: created|appended|no-op`, `path`, `backup_path`) and `record_maps` (with `rows_inserted`, `rows_already_present`, `rows_skipped_not_in_types`).

### Safety rails (carried from Phase 1, plus new ones)
- **D-15:** Before any DB write: take SHA256 of `ddnet-server.sqlite`, take a hot backup via `VACUUM INTO` to `.ddnetcontrol-server-backup-<iso>.sqlite`. Keep at most 3 rolling backups (delete oldest). This gives a concrete recovery path if something goes wrong.
- **D-16:** After the DB write, verify only `record_maps` was affected by reading schema_version and checking that no other table changed row counts (snapshot count per table before and after).
- **D-17:** Write-boundary test in the next verification run must show the diff: server-sqlite hash CHANGED (expected for this phase), cache-sqlite hash unchanged (still SAFE-03), no writes to `maps/`.

### Claude's Discretion
- Exact temp-rename pattern for storage.cfg (`os.replace` vs `shutil.move`). Stick with `os.replace` for consistency with `map_sync.save_state`.
- Whether to VACUUM INTO or plain file copy for DB backup. VACUUM INTO is safer while the DB is live because it takes a consistent snapshot; stick with that.
- Log format for the new module. Reuse the `emit_progress` callback pattern from `map_sync` for consistency.

</decisions>

<specifics>
## Specific Ideas

- The legacy `add_maps.ps1` script in `%APPDATA%\DDNet\` is the **anti-pattern** this phase replaces. It does `DELETE FROM record_maps; INSERT OR IGNORE (..., 'DDNet', 'Unknown')` — the DELETE wipes existing Points/Stars/Mapper accumulated over time. This phase's INSERT OR IGNORE preserves them.
- After Phase 2 runs, the legacy `add_maps.ps1` and `move_maps.ps1` become obsolete. Phase 2 SUMMARY.md documents that fact but does NOT delete the scripts (user's files, user's choice).
- The DDNet mapper uses filename stems as the canonical map name — e.g., `types/novice/Kobra 4.map` → server knows it as `"Kobra 4"`. Server browser shows the same. This is the name that must end up in `record_maps.Map`.

</specifics>

<canonical_refs>
## Canonical References

### Sync engine and Phase 1 contracts
- `tools/map_sync.py` — existing sync. Phase 2 imports `get_ddnet_root`, reuses `save_state` / `load_state` patterns.
- `.planning/phases/01-harden-and-verify-sync-engine/01-SUMMARY.md` — Phase 1 contracts (SAFE-02, SAFE-05 proven)
- `.planning/phases/01-harden-and-verify-sync-engine/evidence/state-snapshot.json` — shape of the manifest Phase 2 reads

### Legacy anti-patterns to avoid
- `C:\Users\rust-\AppData\Roaming\DDNet\add_maps.ps1` (live filesystem) — DELETE then INSERT; destructive
- `C:\Users\rust-\AppData\Roaming\DDNet\move_maps.ps1` (live filesystem) — Move-Item with `(N)` suffix collisions; obsolete

### DDNet engine storage convention
- Official upstream `storage.cfg`: `https://raw.githubusercontent.com/ddnet/ddnet-maps/master/storage.cfg` (uses explicit category paths; we use one recursive parent path because DDNet's `IStorage` resolves recursively)
- `add_path $USERDIR/types` is known to work: confirmed by looking at the DDNet source convention and the fact that our synced `types/` layout matches what upstream installations use.

### DB schema
- Live DB: `C:\Users\rust-\AppData\Roaming\DDNet\ddnet-server.sqlite`
- Schema captured during prior inspection — `record_maps` primary key is `Map` alone, `record_race`/`record_teamrace`/`record_saves` have composite primary keys with `Map`, so preserving `record_maps` keys means downstream join tables stay consistent.
- Backup (pre-phase): `C:\Users\rust-\AppData\Roaming\DDNet\.ddnetcontrol-backup-20260513-020207\ddnet-server.sqlite`

### Requirements
- `.planning/REQUIREMENTS.md` — CFG-01..04, DB-01..04, SAFE-04

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `tools/map_sync.get_ddnet_root(custom_root)` — resolves `%APPDATA%\DDNet` path
- `tools/map_sync.save_state` / `load_state` — temp-then-rename pattern Phase 2 mirrors for `storage.cfg`
- Python stdlib `sqlite3` — no external deps needed

### Established Patterns
- snake_case Python, explicit logging callback, stdlib-only, type hints with `| None`
- Temp-then-rename for atomic writes
- JSON summary returned by every top-level function

### Integration Points
- `sync_ddnet_maps` grows a `register_with_server` kwarg; by default true, so the website and CLI paths get it for free
- Phase 3's web UI will surface the `storage_cfg` + `record_maps` summary fields in its status response
- Phase 4's RCON auto-trigger runs testing-only sync; it too calls `register_with_server=True` so new testing maps get registered

</code_context>

<deferred>
## Deferred Ideas

- Pulling authoritative Mapper/Points/Stars metadata from an upstream catalog (DDNet ranks API) — would change Mapper from `'Unknown'` to real values. Deferred to v1.1 RUNT-03.
- A periodic `VACUUM` of `ddnet-server.sqlite` to reclaim space — not needed for INSERT OR IGNORE workload; defer.
- Deleting the legacy `add_maps.ps1` / `move_maps.ps1` scripts — user's choice, not sync's.

</deferred>

---

*Phase: 02-server-visibility*
*Context gathered: 2026-05-13*
