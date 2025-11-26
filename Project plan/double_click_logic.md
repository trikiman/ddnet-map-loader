Simplified Double-Click Logic (force Tutorial first)

-  **current map**: `Tutorial.map` (e.g., `current.map`)
-  **lastmapname.txt**: real name currently stored inside `Tutorial.map` without `.map` (e.g., `necron`)

0.  **Preflight (idempotent, for portability)**:
    0.1 Set `MAPS_DIR = %APPDATA%\DDNet\maps`.
    0.2 Set `BACKUPS_DIR = %APPDATA%\DDNet\maps\backups`.
    0.3 Ensure directories exist (create if missing): `MAPS_DIR`, `BACKUPS_DIR`.
    0.4 Handle missing files safely:
        - `Tutorial.map`: create a blank file when needed (see Step 3).
        - `lastmapname.txt`: treat as missing and proceed (see Step 4/5).

1.  **User Action**: Operator double-clicks `Grenadium_2.map` (e.g., `new_map.map`).
2.  **Check current server map**:
    2.1 Query the current map (send a command to read the active map name).
    2.2 If it is not `Tutorial`, you will use `change_map Tutorial` in step 7 instead of `hot_reload`.
3.  **Check for existence**:
    3.1 If `Tutorial.map` is missing, create a blank `Tutorial.map`.
    3.2 Ensure the `backups` folder exists; if not, create it.
    3.3 Create a marker file in `C:\\Users\\rust-\\AppData\\Roaming\\DDNet\\maps\\backups\\Tutorial map not exist.map`.
    3.4 If the marker already exists, append a numeric suffix `(1)`, `(2)`, …

4.  **Backup current Tutorial**:
    4.1 Copy `Tutorial.map` to the `backups` folder with a timestamped filename (avoid overwriting; use timestamp).
    4.2 Read `lastmapname.txt` (real name currently represented by `Tutorial.map`).
    4.3 If present, also copy as `backups\\<realname>_<timestamp>.map` (no overwrite).
    4.4 If missing, copy it as `backups\\lastmapname not exist.map`.
5.  **Save last map name**:
    5.1 Overwrite `lastmapname.txt` with the new real name: `"new_map"` (without `.map`), e.g., `Grenadium_2`.
6.  **Copy new map into working file**:
    6.1 Copy `new_map.map` into the DDNet maps directory as `Tutorial.map` (overwrite allowed).
7.  **Hot reload**:
    7.1 Send `hot_reload` so the server reloads `Tutorial.map`.
8.  **Verify**:
    8.1 Confirm successful reload/status.
9.  **Feedback**:
    9.1 Output concise success/failure with relevant paths.


Summary of Naming:
-  **new_map.map**: The map being loaded (example: `Grenadium_2.map`).
-  **current map**: Always `Tutorial.map` in the DDNet maps directory.
-  **lastmapname.txt**: Real map name inside `Tutorial.map` (without extension), e.g., `Grenadium_2`.

Test verifies:
-  Connection and authentication
-  Forced switch to `Tutorial` when needed (via `change_map Tutorial` in step 7)
-  Backup creation (with unique naming; skip self-copy)
-  Replacement of `Tutorial.map` by `new_map.map`
-  Hot reload and verification

You can run this test by executing:
-  Double-click simulation (CLI: `ddnet_control.exe "path\to\new_map.map"`)
-  Regular map changing
