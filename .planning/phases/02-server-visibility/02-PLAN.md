---
phase: 02-server-visibility
plan: 02
status: ready
tasks:
  - id: 1
    title: "New server_register module + unit tests"
    autonomous: true
    tdd: true
  - id: 2
    title: "Execute live storage.cfg install + record_maps registration + verify"
    autonomous: true
  - id: 3
    title: "Author SUMMARY / VERIFICATION / VALIDATION"
    autonomous: true
    checkpoint: human-verify
requirements:
  - CFG-01
  - CFG-02
  - CFG-03
  - CFG-04
  - DB-01
  - DB-02
  - DB-03
  - DB-04
  - SAFE-04
threats:
  - id: T-1
    category: "Tampering"
    description: "DB write could corrupt ddnet-server.sqlite"
    disposition: "mitigated"
    mitigation: "VACUUM INTO snapshot taken before any write; rolling backups kept (3); pre-phase full backup exists at .ddnetcontrol-backup-20260513-020207/"
  - id: T-2
    category: "Tampering"
    description: "DELETE or UPDATE against record_maps wipes player Points/Stars/Mapper (like legacy add_maps.ps1 did)"
    disposition: "mitigated"
    mitigation: "Code only issues INSERT OR IGNORE; unit test test_never_deletes_or_updates_existing_row confirms pre-seeded row byte-identical after run; post-write audit snapshots row counts per other-table and fails loudly if any change"
  - id: T-3
    category: "Tampering"
    description: "storage.cfg backup overwritten if user had a prior .bak"
    disposition: "mitigated"
    mitigation: "ensure_storage_cfg checks for existing .bak and skips the backup copy step; unit test test_never_overwrites_existing_backup confirms"
  - id: T-4
    category: "Information Disclosure"
    description: "VACUUM INTO backup may leak user DB to an unexpected location"
    disposition: "accepted"
    mitigation: "Backup lands inside the same %APPDATA%\\DDNet\\ directory (permissions already user-scoped); retention limited to 3 rolling files"
  - id: T-5
    category: "Denial of Service"
    description: "DDNet server holds write lock on ddnet-server.sqlite, registration hangs indefinitely"
    disposition: "mitigated"
    mitigation: "PRAGMA busy_timeout=5000 (5s); on lock error the registration fails fast with a clear error; user closes DDNet and re-runs"
  - id: T-6
    category: "Tampering"
    description: "Phase 2 writes to a file outside types/** or storage.cfg, violating SAFE-04"
    disposition: "mitigated"
    mitigation: "Code path only opens ddnet-server.sqlite and writes storage.cfg (+.bak); live verification step diffs %APPDATA%\\DDNet\\ pre/post and fails on any unexpected delta"
---

# Phase 2 Plan: Server Visibility — `storage.cfg` + `record_maps`

## Objective

Turn the sync engine's filesystem output into something the local DDNet server can actually load. Two writes: `storage.cfg` (filesystem, idempotent) and `record_maps` rows in `ddnet-server.sqlite` (add-only, non-destructive). Both have explicit safety rails and live-run evidence.

## Tasks

### Task 1 — `tools/server_register.py` + unit tests (COMPLETE)

Already authored and committed as part of the Phase 1 cycle (module added in parallel while Phase 1 sync was running). Tests covered:

- `StorageCfgInstallTest`: create, append, no-op, never-overwrite-bak
- `RecordMapsRegistrationTest`: inserts new + preserves existing, never deletes/updates, testingmaps→testing alias, deduplication, VACUUM-INTO backup taken
- `NoOtherTablesTouchedTest`: `ddnet-cache.sqlite3` SHA unchanged, `maps/Tutorial.map` mtime+bytes unchanged

**Verification:** `python tools/test_server_register.py -v` → 11/11 pass. Already green as of Phase 1 completion.

**Commit:** will roll into Task 2 commit below; the module wasn't committed separately to keep history clean.

### Task 2 — Live execution: install `storage.cfg` + register all synced maps

Run `tools/server_register.py` directly against the live `%APPDATA%\DDNet\` (which now has 1.08 GB of synced maps after Phase 1). Capture the evidence needed for VERIFICATION.md.

**Steps:**

1. Create `tools/verify_phase2.py` that:
   - Takes a pre-snapshot of `%APPDATA%\DDNet\` (DB hashes + maps/downloadedmaps file lists)
   - Reads the pre-run `record_maps` row count + a 20-row sample (Map, Mapper, Points, Stars) so we can prove existing rows are preserved
   - Runs `server_register.register_with_server(ddnet_root)`  — writes storage.cfg + inserts new rows
   - Reads post-run `record_maps` row count + the same 20-row sample; diffs the samples
   - Reads post-run storage.cfg (+ .bak if created)
   - Takes a post-snapshot; diffs pre/post for write-boundary audit
   - Writes evidence files under `.planning/phases/02-server-visibility/evidence/`:
     - `pre-snapshot.json`, `post-snapshot.json`, `write-boundary-diff.txt`
     - `storage-cfg-report.json` (action taken + contents hash + backup path)
     - `record-maps-report.json` (rows_inserted, rows_already_present, backup_path, pre/post counts)
     - `row-preservation-report.json` (20 sample rows before + after, byte-identical diff)
     - `storage-cfg-contents.txt` (full text after install for manual inspection)
2. On any assertion failure write `VERIFICATION-ERROR.txt` and exit 1.

**Commit:** `feat(phase-2): server visibility — storage.cfg install + record_maps registration`

### Task 3 — Phase artifacts

- `02-VERIFICATION.md`: requirement → evidence table for CFG-01..04, DB-01..04, SAFE-04.
- `02-VALIDATION.md`: Nyquist table.
- `02-SUMMARY.md`: what changed, verification numbers, cross-phase handoff for Phase 3+4.

Checkpoint: operator can run `python ddnet_control.exe --rcon-command "sv_map 'Kobra 4'"` (or similar) to confirm CFG-04 — server actually loads the map. If RCON connection unavailable, defer to Phase 4's live CLI verification.

**Commit:** `docs(phase-2): SUMMARY / VERIFICATION / VALIDATION — Phase 2 complete`

## Success criteria

1. `%APPDATA%\DDNet\storage.cfg` exists and contains `add_path $USERDIR/types` line (Phase 2 creates it since it was absent per pre-phase inspection).
2. `ddnet-server.sqlite` has > 2000 new rows in `record_maps` (one per `.map` under `types/`), with `Mapper='Unknown', Points=0, Stars=0`.
3. The pre-seeded `Kobra 4` row (if present — we'll check) keeps its existing Mapper/Points/Stars byte-identical.
4. No row deleted; no row updated; row counts for `record_race`, `record_teamrace`, `record_saves`, `record_points`, and their `_backup` siblings unchanged.
5. `ddnet-cache.sqlite3` SHA256 unchanged (SAFE-03).
6. `maps/` and `downloadedmaps/` file lists unchanged (SAFE-05).
7. 3 phase artifacts committed + 6 evidence files.
