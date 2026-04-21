# Conventions

## General style

The repository favors pragmatic scripting and direct system access over heavy abstraction.

Common characteristics across languages:

- small number of files with broad responsibilities
- imperative control flow
- preference for explicit logging and early returns
- Windows-specific assumptions embedded directly in code and scripts
- limited indirection or dependency injection

## C++ conventions

Observed in `ddnet_control.cpp`:

- Classes use PascalCase: `Logger`, `WsaSession`, `ServerConnection`, `FileLock`
- Free functions use snake_case: `get_current_map`, `handle_map_replacement`, `verify_permissions`
- `fs` is aliased to `std::filesystem`
- Logging goes through `Logger::log(...)` instead of stdout/stderr for the GUI app
- Failures usually return `false` and log an error instead of throwing
- Comments are practical and explain workflow or policy decisions
- Helper types and forward declarations sit near the top of the file

There is also some duplication:

- `validate_map_file` exists as both `std::string` and `fs::path` overloads
- socket helpers are both standalone and partially wrapped in `ServerConnection`

## Python conventions

Observed in `web/server.py` and `tools/*.py`:

- snake_case for functions and variables
- class names in PascalCase such as `MapServerHandler`
- route handling is inline with large `if/elif` chains inside `do_GET()` and `do_POST()`
- JSON responses are built directly in handler methods
- exception handling usually converts failures into HTTP responses or stderr logs

The Python code leans toward single-file scripts rather than packages.

## Frontend conventions

Observed in `web/index.html`, `web/script.js`, and `web/styles.css`:

- one-page static HTML shell
- one large `DOMContentLoaded` block in `web/script.js`
- plain DOM APIs and `fetch()` rather than a framework
- CSS custom properties for light/dark theme tokens
- inline style attributes are mixed with stylesheet-defined classes

UI copy mixes English labels with some Russian captions in `web/index.html`.

## Script conventions

Batch and PowerShell scripts are written as task-specific utilities:

- parameter blocks are used in PowerShell watchers such as `auto_uploader.ps1`
- batch files use `@echo off`, `cd /d "%~dp0"`, and explicit local paths
- several scripts hardcode absolute Windows paths instead of computing them dynamically

Examples:

- `compile.bat`
- `copy_dlls.bat`
- `web/create_shortcut.bat`
- `fix_file_association.bat`

## Error-handling patterns

Error handling is consistent but basic:

- native code logs and returns failure
- web server returns JSON error objects with status codes
- helper tools print diagnostics to stderr
- retries are implemented manually where needed, such as `ServerConnection` and upload watcher logic

There is little evidence of centralized exception policy, structured error types, or automated recovery outside targeted retry loops.

## Path and configuration conventions

Important conventions baked into the code:

- DDNet maps live under `%APPDATA%\\DDNet\\maps`
- backups live under `%APPDATA%\\DDNet\\maps\\backups`
- the working hot-reload target is `Tutorial.map`
- `.map` file association is written under `HKCU\\Software\\Classes`
- local web server defaults to port `8299`
- DDNet econ/RCON defaults to `127.0.0.1:8303`

## Repo hygiene conventions

The repo does not currently follow a strict "source only" convention.

Observed tracked/generated items:

- `ddnet_control.exe`
- `web/server.log`
- `test.map`
- icon binaries under `Image/` and `web/`

That convention may be intentional for a local utility project, but it differs from a typical clean-source repository layout.
