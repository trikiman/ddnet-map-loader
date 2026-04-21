# Architecture

## System shape

This is not a single cohesive service. It is a small product family built around one native executable and one optional companion web server.

Main execution surfaces:

- `ddnet_control.cpp` - native Windows executable for map replacement and restore flows
- `web/server.py` - local HTTP server and tray application for uploading/downloading maps
- `auto_uploader.ps1` - file watcher that bridges editor saves into the web server upload API

The two runtime paths share the DDNet maps directory rather than sharing an internal application module.

## Native executable architecture

`ddnet_control.cpp` is a monolithic implementation file that contains:

- platform setup
- logging
- socket management
- file validation
- backup and restore logic
- registry/file-association setup
- Windows GUI entry point

Important internal abstractions in `ddnet_control.cpp`:

- `Logger` - centralized append-only file logger
- `WsaSession` - RAII wrapper for `WSAStartup` / `WSACleanup`
- `MapInfo` - state for backup/original/replacement paths
- `ServerConfig` - socket timeout and retry constants
- `ServerConnection` - retry wrapper around socket connect/send/receive
- `FileLock` - coarse exclusive file lock during copy operations

Despite those helpers, the architecture remains largely procedural.

## Native control flow

Observed top-level flow from `WinMain` in `ddnet_control.cpp`:

1. Convert Windows command line arguments into UTF-8 strings
2. Initialize logging and Winsock
3. Branch to setup mode when `is_setup_command()` matches
4. Branch to restore mode when `is_restore_command()` matches
5. Validate map path and map file contents
6. Verify DDNet server availability with `is_server_running()`
7. Connect and authenticate to the server
8. Clean old backups
9. Run `handle_map_replacement()`

`handle_map_replacement()` is the central business workflow:

1. Resolve/create maps and backups directories
2. Query current server map
3. Ensure `Tutorial.map` exists as the working map
4. Create timestamped backup markers and backup copies
5. Copy the incoming map into the DDNet maps directory if needed
6. Update `lastmapname.txt`
7. Overwrite `Tutorial.map`
8. Send either `change_map Tutorial` or `hot_reload`
9. Verify server responsiveness with `status`

## Web application architecture

`web/server.py` combines static file serving, JSON APIs, and desktop integration in a single Python process.

Server-side architectural pieces:

- `MapServerHandler(SimpleHTTPRequestHandler)` handles routing inline
- `do_GET()` serves static files and read-only APIs
- `do_POST()` handles upload, click simulation, watcher startup, and file lookup
- `create_tray_icon()` adds desktop tray controls
- `run_server()` binds the server, hides the console, and starts the tray loop

Client-side architectural pieces:

- `web/index.html` defines a single-page shell
- `web/script.js` owns all behavior inside one `DOMContentLoaded` callback
- `web/styles.css` provides theme variables and component styling

This is a classic "static page + imperative DOM + thin Python backend" layout with no formal API layer or module system.

## Data flow between subsystems

The dominant data flow is filesystem-mediated:

- User drops/selects `.map` file in `web/index.html`
- `web/script.js` uploads to `POST /upload`
- `web/server.py` writes the file into `%APPDATA%\\DDNet\\maps`
- `web/server.py` optionally launches the file via PowerShell
- Windows file association opens `ddnet_control.exe`
- `ddnet_control.cpp` performs the backup/reload workflow against the DDNet server

The auto-update flow adds one more hop:

- local editor save
- `auto_uploader.ps1` file event
- `POST /upload`
- write to DDNet map directory
- silent `Start-Process`

## Architectural boundaries

The codebase has only soft boundaries:

- Native code is isolated in `ddnet_control.cpp`, but as one large file
- Web code is isolated in `web/`, but routing, UI logic, and desktop behavior are still tightly coupled
- Helper utilities in `tools/` are separate from product runtime
- Planning and process notes live in `Project plan/`, `scratchpad.md`, and `RELEASE_CHECKLIST.md`

There is no shared domain model package, no test harness module, and no reusable internal library layer across native and web code.

## Entry points

Important entry points to know before changing the repo:

- `compile.bat` - native build entry point
- `int WINAPI WinMain(...)` in `ddnet_control.cpp` - native app runtime entry point
- `if __name__ == '__main__': run_server()` in `web/server.py` - web runtime entry point
- `web/run_server.bat` - convenience launcher for the web server
- `auto_uploader.ps1` - watcher runtime entry point for save-triggered uploads

## Design summary

The design favors directness and local automation over modularity:

- minimal dependencies for the core product
- direct use of OS features
- direct socket and filesystem operations
- minimal abstraction around HTTP and UI

That makes the repo easy to run locally, but the lack of module boundaries will raise the cost of larger changes.
