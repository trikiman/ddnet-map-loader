# Concerns

## High-priority concerns

### Hardcoded credentials and local control assumptions

The DDNet control path uses hardcoded or sample credentials in multiple places:

- `authenticate()` in `ddnet_control.cpp` sends `test123`
- `myServerconfig.cfg` stores `sv_rcon_password "test123"` and `ec_password "test123"`

That is acceptable for a local prototype, but it is a real security risk once the server or repo is shared beyond one machine.

### Upload surface is effectively unauthenticated

`web/server.py` accepts uploads at `POST /upload`, but the token check is optional:

- if `X-Upload-Token` is present and invalid, the request fails
- if the header is omitted entirely, upload is allowed

Combined with:

- `Access-Control-Allow-Origin: *` in `end_headers()`
- binding to `0.0.0.0:8299` in `run_server()`
- a tray menu entry for public URL `http://185.60.44.131:8299`

the current web server is much more exposed than the project structure suggests.

### Monolithic native implementation

`ddnet_control.cpp` contains almost the entire native application in one file, including:

- socket handling
- registry writes
- validation
- backup policy
- runtime control flow
- Windows entry point

That makes changes easy to start but harder to review, test, and isolate.

## Medium-priority concerns

### Hardcoded machine-specific scripts

Several scripts assume one specific workstation layout:

- `compile.bat` calls `E:\\Program files\\Microsoft Visual Studio\\2022\\Community\\VC\\Auxiliary\\Build\\vcvars64.bat`
- `copy_dlls.bat` copies from `E:\\Users\\rust-\\CascadeProjects\\ddnet_control_old\\...`
- `web/create_shortcut.bat` points directly to `E:\\Projects\\ddnetcontrol\\web\\server.py`

That reduces portability and makes onboarding harder.

### Repository contains tracked binaries and logs

Tracked non-source artifacts include:

- `ddnet_control.exe`
- `web/server.log`
- `test.map`
- several `.ico` binaries

This can blur the source-of-truth boundary and create noisy diffs or accidental distribution of stale artifacts.

### Documentation and implementation drift

There are visible mismatches between documentation and code:

- `README.md` refers to `registry/` scripts that are not present in the current tree
- `README.md` emphasizes `Image/ddnet_loader.ico`
- `ddnet_control.rc` actually references `Image\\ddnet.ico`
- file association helpers prefer `Image\\ddnet_loader.ico`

That drift will confuse packaging and troubleshooting.

### Duplicate files without an obvious canonical source

Examples of duplicated content:

- `auto_uploader.ps1` and `web/auto_uploader.ps1`
- `ddnet_loader.ico` and `Image/ddnet_loader.ico`

Duplication increases the chance that one copy changes while the other silently goes stale.

## Lower-priority but notable concerns

### Deprecated Python module usage

`web/server.py` imports `cgi`, which is deprecated in modern Python and removed in newer releases. That may become a runtime blocker during future Python upgrades.

### Limited automated testing

The repo includes testing dependencies in `requirements.txt`, but there is no visible automated test suite or CI workflow. The current manual-only approach is risky for backup/reload logic and upload endpoint behavior.

### Mixed-purpose repository

The repo combines product code, editor-assistant tooling, process notes, binaries, and local scripts in one tree:

- product code in `ddnet_control.cpp` and `web/`
- helper automation in `tools/`
- planning docs in `Project plan/`
- editor guidance in `.windsurfrules` and `README_devin.cursorrules.md`

That is manageable for a solo workspace, but it weakens packaging clarity and makes "production code" harder to identify quickly.

## Recommended cleanup order

If this repo is being stabilized, the most valuable cleanup order is:

1. lock down or local-only the web upload surface
2. externalize passwords, ports, and workstation-specific paths
3. split native logic out of `ddnet_control.cpp` into smaller units
4. remove or formalize tracked binaries/logs
5. add a minimal automated smoke suite for web and native pure helpers
