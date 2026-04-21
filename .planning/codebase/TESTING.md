# Testing

## Current state

There is no real automated test suite in the inspected repository.

What is present:

- `test.map` - a sample artifact for manual runtime validation
- `scratchpad.md` - ad hoc notes about recent manual testing work
- `RELEASE_CHECKLIST.md` - manual release and verification checklist
- `/test` endpoint in `web/server.py` - lightweight server health check
- built-in map validation logic in `ddnet_control.cpp`

What is absent:

- no `tests/` directory
- no `pytest` test files
- no C++ unit test project
- no CI workflow under `.github/`
- no browser automation or API contract tests

## Native executable verification

The native path relies on runtime/manual checks:

- `compile.bat` is the build smoke test
- `validate_map_file(...)` in `ddnet_control.cpp` checks map header structure before use
- `is_server_running()` and socket auth checks provide runtime preflight validation
- `RELEASE_CHECKLIST.md` documents manual CLI execution using `ddnet_control.exe "<map path>"`
- logs are expected in `ddnet_control.log`

This is useful for operational safety, but it is not a substitute for repeatable automated tests.

## Web server verification

The Python web app currently appears to be verified manually:

- `web/run_server.bat` launches the service
- `GET /test` in `web/server.py` returns a simple health payload
- `web/script.js` logs client-side behavior to the browser console
- the UI can be checked by loading `web/index.html` through the running server
- `web/server.log` suggests runtime observation is part of the current workflow

There is no explicit API test harness for upload/download/folder-list endpoints.

## Helper tool verification

The scripts under `tools/` look script-driven rather than test-driven:

- `tools/search_engine.py` has no tests
- `tools/web_scraper.py` has no tests
- `tools/llm_api.py` has no tests
- `tools/screenshot_utils.py` has no tests

The root `requirements.txt` includes `pytest`, `pytest-asyncio`, and `unittest2`, but there are no visible test files using them.

## Testing risks

The largest testing gaps are around system boundaries:

- DDNet socket interactions in `ddnet_control.cpp`
- backup/restore correctness in `handle_map_replacement()`
- Windows registry/file association behavior
- upload and auto-reload flows in `web/server.py` + `web/script.js`
- security-sensitive edge cases for file upload and path handling

Because the project is Windows-specific and filesystem-heavy, those flows are also the hardest to validate manually at scale.

## Suggested first automated coverage

If automated testing is added, the highest-yield starting points are:

- pure validation helpers in `ddnet_control.cpp` such as map header checks and lastmap parsing
- Python filename sanitization and path-safety helpers in `web/server.py`
- upload endpoint behavior for invalid extension, oversize file, and locked file paths
- frontend smoke verification for basic map list rendering and upload UI wiring

## Practical takeaway

Today the repo is set up for manual confidence, not regression prevention.

Any significant refactor should budget time for at least:

- a small Python API test layer around `web/server.py`
- a few native unit tests for pure helper logic extracted from `ddnet_control.cpp`
- one end-to-end Windows smoke script covering upload -> open -> reload
