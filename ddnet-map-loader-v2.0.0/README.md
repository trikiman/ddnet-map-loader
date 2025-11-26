# DDNet Map Loader v2 (Portable)

A tiny helper that lets you double‑click any `.map` file to hot‑reload it on your local DDNet server. It also makes backups and logs what happened.

## 📋 Requirements
- Windows 10/11 (no admin needed)
- DDNet client/server installed and a local server you can reach

## 🤔 What this is (and why)
- Associates `.map` files with this app.
- When you double‑click a map, it will:
  - Check the map file
  - Back up your current map
  - Replace the working map and send `hot_reload`
  - Log to `%APPDATA%\DDNet\maps\ddnet_control.log`
- Great for fast map testing while you build.

## 🚀 How to use (Quick)
1) Check/move `myServerconfig.cfg`
   - Find your DDNet `data` folder (see below) and copy `myServerconfig.cfg` into it (optional but recommended).
2) Associate `.map` files with this EXE (recommended way)
   - Right‑click any `.map` file → Open with → Choose another app → More apps → Look for another app on this PC
   - Select `ddnet_control.exe` in this folder
   - Tick "Always use this app to open .map files" and confirm
   - Verify the `.map` icon changed. If not, see Troubleshooting below.
   - Advanced (optional): you can also run `registry\setup_map_association_current_user.bat` to register it for your user automatically, then restart Windows Explorer.
3) Double‑click any `.map`
   - Example: `%APPDATA%\\DDNet\\maps\\mapsfortest\\anymap.map`
   - The file’s icon should have the new loader icon (may show a small arrow overlay if a shortcut).
4) Check logs
   - `%APPDATA%\\DDNet\\maps\\ddnet_control.log` (shows validation, backup, reload status)

## 📁 Where to put myServerconfig.cfg
- Simple way to find your DDNet `data` folder:
  1) Right‑click your DDNet shortcut (on taskbar/Start/Desktop) → Open file location
  2) In the opened folder, go to the `ddnet` directory (where `DDNet.exe` lives)
  3) Open the `data` subfolder → copy `myServerconfig.cfg` here
- Common locations (examples; yours may differ):
  - Steam default: `C:\Program Files (x86)\Steam\steamapps\common\DDraceNetwork\ddnet\data`
  - Steam (other library): `<YourSteamLibrary>\steamapps\common\DDraceNetwork\ddnet\data`
  - Non‑Steam/portable: the `data` folder next to `DDNet.exe`

## 🧰 Troubleshooting
- __Console flashes and closes__
  - Windows likely didn’t pass the file path. Re‑associate via Open with (step 2) or run the setup script and restart Explorer.
- __App not in “Open with”__
  - Use Open with → Choose another app → More apps → Look for another app on this PC → pick `ddnet_control.exe` → check “Always use this app”.
- __Icon didn’t update__
  - Restart Windows Explorer. Icon cache is stubborn on Windows.
- __No hot‑reload__
  - Make sure your local server is running (127.0.0.1:8303) and RCON settings are correct.
  - Check `%APPDATA%\\DDNet\\maps\\ddnet_control.log` for the exact reason.
- __Undo the association__
  - Run: `registry\\remove_map_association_current_user.bat`

## 📂 What’s inside
- `ddnet_control.exe`
- `ddnet_loader.ico`
- `myServerconfig.cfg`
- `registry/`
  - `setup_map_association_current_user.bat`
  - `remove_map_association_current_user.bat`
