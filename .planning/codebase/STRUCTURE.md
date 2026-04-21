# Structure

## Top-level layout

The repository is organized as a small Windows app workspace rather than a conventional library/application split.

Top-level items with active product relevance:

- `ddnet_control.cpp` - primary native application source
- `ddnet_control.rc` - Windows resource file
- `compile.bat` - native build command
- `fix_file_association.bat` - registry-based file association repair
- `auto_uploader.ps1` - root-level file watcher/uploader
- `myServerconfig.cfg` - sample DDNet server config
- `requirements.txt` - Python dependencies for helper tooling
- `README.md` - end-user/developer overview
- `RELEASE_CHECKLIST.md` - manual release flow
- `scratchpad.md` - ad hoc working notes

Primary directories:

- `Image/` - icon assets for the native application
- `web/` - optional Python web server and static browser UI
- `tools/` - support utilities for LLM access, scraping, screenshots, and icon generation
- `Project plan/` - planning notes and freeform project docs
- `.devcontainer/` - devcontainer metadata
- `.vscode.example/` - example editor settings
- `.planning/codebase/` - generated codebase map documents

## Native area

The native app is intentionally flat:

- `ddnet_control.cpp` contains nearly all native business logic
- `ddnet_control.rc` handles version metadata and icon binding
- `compile.bat` handles build orchestration
- `vcvars64.bat` exists as a local helper

There is no `src/`, `include/`, or per-feature C++ directory split.

## Web area

The `web/` directory is a self-contained mini app:

- `web/server.py` - backend and tray host
- `web/index.html` - main page
- `web/script.js` - client logic
- `web/styles.css` - styles
- `web/run_server.bat` - launcher
- `web/create_shortcut.bat` - desktop shortcut helper
- `web/auto_uploader.ps1` - duplicate of the root watcher
- `web/map.ico`, `web/map.png`, `web/*.svg` - UI/tray assets
- `web/requirements.txt` - runtime dependencies
- `web/server.log` - currently tracked runtime log artifact

This folder is the closest thing to a bounded subsystem in the repo.

## Tools area

The `tools/` directory groups support scripts:

- `tools/llm_api.py`
- `tools/search_engine.py`
- `tools/web_scraper.py`
- `tools/screenshot_utils.py`
- `tools/convert_ico.py`
- `tools/create_unstable_icon.ps1`

These scripts appear to support local development workflows and editor automation rather than the DDNet runtime path.

## Planning and process docs

Several non-code documents are kept alongside the source:

- `Project plan/01-Idea.md`
- `Project plan/05-plan.md`
- `Project plan/06-next-story.md`
- `Project plan/07-fix-resume.md`
- `Project plan/08-post-mortem.md`
- `Project plan/09-fix-codebase.md`
- `rules.md`
- `.windsurfrules`
- `README_devin.cursorrules.md`

That suggests the repository doubles as both implementation workspace and process notebook.

## Naming and placement patterns

Observed naming tendencies:

- Root scripts use descriptive snake_case or lowercase batch names such as `fix_file_association.bat`
- C++ free functions in `ddnet_control.cpp` are mostly snake_case
- Python files under `tools/` and `web/` also use snake_case
- Asset names are inconsistent across `ddnet_loader.ico`, `ddnet.ico`, `ddnet-unstable.ico`, and `web/map.ico`

## Duplicate or overlapping files

There are a few duplicated or overlapping assets:

- `auto_uploader.ps1` and `web/auto_uploader.ps1` have identical content
- `ddnet_loader.ico` and `Image/ddnet_loader.ico` have identical content
- Icon references differ across `ddnet_control.rc`, `README.md`, and `fix_file_association.bat`

These should be treated as structural noise until the canonical source of truth is clarified.

## Sparse or inactive areas

Some directories exist but do not appear active from the inspected tree:

- `.github/` exists but contains no workflow/config files in the current checkout
- `wsl/` exists but appears empty

## Generated and committed artifacts

The repository currently tracks artifacts that many teams would ignore:

- `ddnet_control.exe`
- `test.map`
- `web/server.log`
- several `.ico` binaries

That affects repo cleanliness, review noise, and release habits.
