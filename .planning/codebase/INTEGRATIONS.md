# Integrations

## Core product integration: DDNet server control

The main executable in `ddnet_control.cpp` integrates directly with a local DDNet server through its econ/RCON socket.

Observed touchpoints:

- `authenticate()` in `ddnet_control.cpp` sends the password over the socket
- `get_current_map()` in `ddnet_control.cpp` queries the active map
- `change_map()` in `ddnet_control.cpp` sends `change_map <name>`
- `hot_reload_map()` and `handle_map_replacement()` in `ddnet_control.cpp` send `hot_reload`
- `myServerconfig.cfg` defines `sv_port 8303`, `ec_port 8303`, `ec_bindaddr "127.0.0.1"`, and matching passwords

This is the main integration boundary for the native tool.

## Filesystem integration

Both the native tool and the web server depend heavily on the user's DDNet data directory:

- `%APPDATA%\\DDNet\\maps` is resolved in `ddnet_control.cpp`
- `MAPS_FOLDER` in `web/server.py` points to `~\\AppData\\Roaming\\DDNet\\maps`
- `ddnet_control.cpp` writes `ddnet_control.log`, `backup_info.txt`, `lastmapname.txt`, and backup files under `backups/`
- `web/server.py` lists, uploads, downloads, and searches `.map` files in the same DDNet folder tree

This shared filesystem folder is effectively the integration bus between the native app, the web UI, and DDNet itself.

## Windows shell integration

The project integrates with several Windows desktop features:

- Registry-based file association setup in `setupFileAssociation()` inside `ddnet_control.cpp`
- Registry-based file association repair in `fix_file_association.bat`
- Shell launching of `.map` files from `web/server.py` using PowerShell `Start-Process`
- Desktop shortcut creation in `web/create_shortcut.bat`
- System tray integration in `create_tray_icon()` inside `web/server.py`
- Native file picker integration in the `/browse-file` handler in `web/server.py`
- Clipboard integration in `copy_to_clipboard()` in `web/server.py`

The product is therefore tightly coupled to Windows rather than being cross-platform.

## Local HTTP integration

The optional Python server in `web/server.py` exposes a local HTTP API consumed by `web/script.js`.

Important endpoints:

- `/list-maps`
- `/list-folders`
- `/list-maps-folder/<folder>`
- `/download/<name>`
- `/download-folder/<folder>/<name>`
- `/upload`
- `/simulate-click`
- `/find-map`
- `/browse-file`
- `/start-auto-update`
- `/get-logs`
- `/issue-token`
- `/test`

The browser client in `web/script.js` uses `fetch()` against those endpoints for uploads, downloads, sorting, logs, and watcher startup.

## PowerShell upload watcher integration

The browser can start a local file watcher that auto-uploads on save:

- `web/script.js` calls `/start-auto-update`
- `web/server.py` launches `auto_uploader.ps1`
- `auto_uploader.ps1` and `web/auto_uploader.ps1` monitor a selected file using `FileSystemWatcher`
- The watcher posts multipart uploads back to `POST /upload`

This creates a loop from local editor save -> PowerShell watcher -> local HTTP server -> DDNet map folder -> silent file open / reload.

## External network and public URL assumptions

`web/server.py` binds `HTTPServer` to `0.0.0.0:8299`, and the tray menu includes:

- `http://localhost:8299`
- `http://185.60.44.131:8299`

That indicates the web server is intended for both local and LAN/public access, even though there is no substantial authentication layer around most endpoints.

## AI and search provider integrations

Helper tooling under `tools/` integrates with third-party services:

- `tools/llm_api.py` - OpenAI
- `tools/llm_api.py` - Azure OpenAI
- `tools/llm_api.py` - Anthropic
- `tools/llm_api.py` - Google Gemini
- `tools/llm_api.py` - DeepSeek
- `tools/llm_api.py` - SiliconFlow
- `tools/search_engine.py` - DuckDuckGo Search
- `tools/web_scraper.py` - Playwright browser automation

These are not wired into the product runtime in the files inspected, but they are still live integrations present in the repository.

## Asset and resource integration

Windows resource and icon usage spans multiple locations:

- `ddnet_control.rc` points at `Image\\ddnet.ico`
- `README.md` documents `Image/ddnet_loader.ico`
- `fix_file_association.bat` prefers `Image\\ddnet_loader.ico`
- `web/create_shortcut.bat` points at `web\\map.ico`

The project uses multiple icon assets and multiple launch surfaces, so icon/resource consistency matters for packaging.
