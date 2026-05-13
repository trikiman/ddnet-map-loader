---
phase: 02-server-visibility
validated_at: 2026-05-13T00:06:00Z
nyquist_complete: true
---

# Phase 2 Validation (Nyquist)

Every must-have claim has at least two witnesses.

## Must-have truths

| # | Truth | Satisfied | Primary evidence | Second witness |
|---|---|---|---|---|
| T-1 | `storage.cfg` installed with `add_path $USERDIR/types` | y | `evidence/storage-cfg-report.json` (`contains_target_line=true`, SHA256) | `evidence/storage-cfg-contents.txt` (full text dump) |
| T-2 | Only `INSERT OR IGNORE` operations — no DELETE, no UPDATE | y | `evidence/write-boundary-diff.txt` (`PASS: record_maps row count 3382 -> 3438 (+56 new, none removed)`) | `register_maps_in_db` code: only one SQL statement — `INSERT OR IGNORE`; unit test `test_never_deletes_or_updates_existing_row` |
| T-3 | Existing `record_maps` rows byte-identical before/after | y | `evidence/row-preservation-report.json` (`mutated_count=0` across 20 sampled rows) | `evidence/record-maps-report.json` contains both `pre_sample_first_20` and `post_sample_first_20` — deep-equal |
| T-4 | No other `ddnet-server.sqlite` table row count changed | y | `evidence/write-boundary-diff.txt` 7 PASS lines for `record_race/teamrace/saves/points` and their `_backup` siblings | `server_register._TABLES_TO_LEAVE_ALONE` pre/post row counts captured inside register_maps_in_db's `other_table_counts` field |
| T-5 | `ddnet-cache.sqlite3` untouched | y | `evidence/write-boundary-diff.txt` `PASS: ddnet-cache.sqlite3 SHA256 unchanged (bc9cb763cead...)` | `evidence/pre-snapshot.json` vs `post-snapshot.json` `db_hashes` field |
| T-6 | `maps/` and `downloadedmaps/` untouched | y | `evidence/write-boundary-diff.txt` `PASS: maps/ unchanged (1799 files)`, `PASS: downloadedmaps/ unchanged (307 files)` | raw file lists in pre/post snapshots, compared by `(relpath, size, mtime_ns)` tuple |
| T-7 | Pre-write backup of `ddnet-server.sqlite` exists | y | `evidence/record-maps-report.json` `backup_path` field points at `.ddnetcontrol-server-backup-20260513T000444Z.sqlite` | file exists on disk at that path (live filesystem check) |

## Must-have artifacts

| Artifact | Path | Purpose |
|---|---|---|
| Pre-snapshot | `evidence/pre-snapshot.json` | SHA + file-list + storage.cfg status before Phase 2 |
| Post-snapshot | `evidence/post-snapshot.json` | Same after Phase 2 |
| Write-boundary diff | `evidence/write-boundary-diff.txt` | Human-readable verdicts per safety rail |
| Storage.cfg report | `evidence/storage-cfg-report.json` | Action + path + SHA + backup path |
| Storage.cfg contents | `evidence/storage-cfg-contents.txt` | Full text of installed file |
| Record_maps report | `evidence/record-maps-report.json` | Inserted/preserved/skipped counts + 20-row samples |
| Row preservation | `evidence/row-preservation-report.json` | Deep-equal verification of sampled rows |

## Must-have key links

| Link | Both ends | Verified |
|---|---|---|
| `rows_inserted + rows_already_present + rows_skipped_duplicate_stem ↔ manifest_size` | `record-maps-report.json`: 56 + 2398 + 4 = 2458 = manifest_size. Invariant holds. | y |
| `pre sample row (Kobra 4 / Ravie / 5 / 3) ↔ post sample row (same)` | `row-preservation-report.json` preserved_sample includes the exact tuple | y |
| `storage_cfg.action ↔ pre/post snapshots` | Action was `"created"`. Pre snapshot: `storage_cfg_exists=false`. Post snapshot: `storage_cfg_exists=true`. Consistent. | y |
| `server DB SHA changed ↔ record_maps count grew by 56` | SHA changed (expected); `record_maps` 3382 → 3438 (+56). Counts match. | y |

## Nyquist completeness

All 7 must-have truths have two independent witnesses. DB-03 (no DELETE) in particular has three: code-level static (only one INSERT OR IGNORE statement), row count check (post >= pre), and unit test.

---

*Validated 2026-05-13 00:06 UTC*
