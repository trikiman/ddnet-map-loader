# DDNet Map Loader (v2)

Source code for a helper tool that hot-reloads a DDNet server map and manages backups.

- Language: C++ (single binary)
- Main: `ddnet_control.cpp`
- Icon/Resources: `ddnet_control.rc` (uses `Image/ddnet_loader.ico`)
- Registry scripts (user-scope): `registry/`
- Tools: `tools/` (e.g., `convert_ico.py` for multi-size ICO generation)
- Web UI assets (optional): `web/`

## Build

Windows with MSVC (VS 2022 Build Tools):

```bat
compile.bat
```

On success: `ddnet_control.exe` is produced; see `build.log`.

## Usage

Double-click a `.map` file (after association), or run from CLI to load a map and hot-reload:

```bat
ddnet_control.exe "C:\\Users\\<you>\\AppData\\Roaming\\DDNet\\maps\\mapsfortest\\Tutorial.map"
```

Behavior (high level):
- Detect current server map via `sv_map`.
- Ensure `%APPDATA%/DDNet/maps` structure (and `backups/`).
- Copy new map into DDNet maps (LINEAR2) if needed.
- Manage `lastmapname.txt` to decide backup/restore behavior.
- Replace working `current_map.map` (LINEAR3) and send `hot_reload`.

## File association (Current User)

Scripts are user-scope only, safe to run without admin:

- Remove .map association and residues:
  ```bat
  registry\remove_map_association_current_user.bat
  ```
- Associate `.map` to this build:
  ```bat
  registry\setup_map_association_current_user.bat
  ```

If Explorer icons look stale, restart Windows Explorer or clear the icon cache:

```bat
ie4uinit.exe -ClearIconCache
```

## Icons

- EXE embeds `Image/ddnet_loader.ico` via `ddnet_control.rc`.
- If needed, generate a multi-size ICO:
  ```bat
  venv\Scripts\python.exe tools\convert_ico.py Image\ddnet_loader.ico Image\ddnet_loader_fixed.ico
  ```
  Then update `ddnet_control.rc` to use the fixed icon and rebuild.

## Development notes

- RCON defaults in code: host `127.0.0.1:8303`, password `test123` (adjust as needed).
- Logs: `ddnet_control.log` (and `build.log` for builds).
- See `scratchpad.md` for current test plan and status.

## License

MIT (or your preferred license).