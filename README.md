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

## Server connection (econ)

`ddnet_control.exe` talks to the local DDNet server over the **external console (econ)** TCP socket on `127.0.0.1:8303`. It does **not** use the in-game RCON channel — `sv_rcon_password` is irrelevant here. The password it sends is `ec_password`.

The password is resolved at runtime, in this order (first non-empty wins):

1. `DDNETCONTROL_ECON_PASSWORD` environment variable.
2. `econ_password=<value>` in a `ddnet_control.cfg` file placed next to `ddnet_control.exe`.
3. `ec_password "<value>"` from `%APPDATA%\DDNet\autoexec_server.cfg` (DDNet's USERDIR autoexec — overrides anything `exec`'d from it).
4. `ec_password "<value>"` from the running `DDNet-Server.exe`'s `data/myServerConfig.cfg`.
5. `ec_password "<value>"` from the running `DDNet-Server.exe`'s `data/autoexec_server.cfg`.
6. Hardcoded fallback `test123` (a `WARNING` is logged so you notice).

Within a single cfg file, the **last** `ec_password` line wins, matching DDNet's "later command overrides" semantics. The chosen source is logged to `ddnet_control.log` (the password value itself is never logged).

If your server uses a non-default `ec_password`, you don't need to recompile — set `DDNETCONTROL_ECON_PASSWORD` or drop a `ddnet_control.cfg` next to the EXE:

```ini
# ddnet_control.cfg (next to ddnet_control.exe)
econ_password=your-password-here
```

Host/port are still `127.0.0.1:8303` in the binary (matches DDNet's default `ec_port`/`ec_bindaddr`).

## Development notes

- Logs: `ddnet_control.log` (and `build.log` for builds). Default location is `%APPDATA%\DDNet\maps\ddnet_control.log` (the EXE's working directory when launched via `.map` double-click).
- See `scratchpad.md` for current test plan and status.

## License

MIT (or your preferred license).