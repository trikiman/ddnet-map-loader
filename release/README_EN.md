# DDNet Map Loader - User Guide

## Overview
DDNet Map Loader is a tool that allows you to quickly replace maps on your DDNet server while preserving player positions using the hot reload feature.

## Requirements
1. DDNet Server installed on your computer
2. Server configured with ECON password (instructions below)
3. Maps located in the DDNet maps directory (instructions below)

## Maps Setup
1. Create the maps directory if it doesn't exist:
   ```
   C:\Users\[YourUsername]\AppData\Roaming\DDNet\maps
   ```
2. Copy the provided `tutorial.map` from the `maps` folder to:
   ```
   C:\Users\[YourUsername]\AppData\Roaming\DDNet\maps\tutorial.map
   ```
   This is required as it's the default map for the server.

3. Any additional maps you want to use should also be placed in this directory.

Note: The maps folder is empty by default after DDNet installation. Without the tutorial map, the server and map loader won't work properly.

## Server Setup
1. Navigate to your DDNet server directory (e.g., `C:\Users\[YourUsername]\Desktop\DDNet-18.7-win64\`)
2. Go to the `data` folder
3. Copy the provided `myServerconfig.cfg` file to this folder
4. Start your server using the command:
   ```batch
   DDNet-Server.exe -f myServerconfig.cfg
   ```

### Server Configuration Details
The provided `myServerconfig.cfg` contains:
```
sv_name "DDNet Map Loader Server"    # Server name
sv_port 8303                         # Game port
sv_max_clients 16                    # Maximum players
sv_rcon_password "test123"          # Admin password
sv_rcon_mod_password "test123"      # Moderator password
ec_port 8303                        # External console port
ec_password "test123"               # External console password (used by Map Loader)
ec_bindaddr "127.0.0.1"            # Listen only on localhost
sv_map "tutorial"                   # Initial map (must exist in maps folder)
```

You can modify these settings as needed, but make sure to:
1. Keep `ec_port` and `ec_password` matching the Map Loader settings
2. Keep `ec_bindaddr` as "127.0.0.1" for security
3. Update the passwords for better security
4. Make sure `sv_map` points to a map that exists in your maps folder

## Installation
1. Place `ddnet_control.exe` in any folder
2. Double-click any `.map` file to use it with the loader

## Usage
### Method 1: Double-Click
1. Simply double-click any `.map` file you want to load
2. The tool will automatically:
   - Create a backup of the current map
   - Replace the current map with the new one
   - Hot reload the server to preserve player positions

### Method 2: Command Line
```batch
ddnet_control.exe [map_path] [options]
```
Options:
- `--skip-backup`: Skip creating backup
- `--restore`: Restore the last backup instead of replacing the map

## Directory Structure
Here's the complete directory structure you need:
```
C:\Users\[YourUsername]\AppData\Roaming\DDNet\
└── maps\
    ├── tutorial.map      # Required default map
    └── [your maps].map   # Your additional maps

C:\Users\[YourUsername]\Desktop\DDNet-18.7-win64\
└── data\
    └── myServerconfig.cfg    # Server configuration
```

## Troubleshooting
1. If the program can't connect to the server:
   - Make sure your DDNet server is running with the correct config
   - Check if the ECON password in `myServerconfig.cfg` matches
   - Verify the server is using the correct port (8303)

2. If map replacement fails:
   - Check if you have write permissions in the maps directory
   - Make sure the map file isn't being used by another process
   - Verify that the maps directory exists at `%AppData%\DDNet\maps`

3. If the server won't start:
   - Make sure the tutorial.map exists in your maps directory
   - Check that the map specified in `sv_map` exists
   - Verify all paths and permissions are correct

## Security Notes
- The default passwords in the config file are for testing only
- In a production environment, change all passwords to strong, unique values
- The external console is bound to localhost only for security
- Only share the server config with trusted administrators

## Notes
- The program automatically creates backups before replacing maps
- Player positions are preserved during map changes
- The server must be running for the tool to work
- Always keep a copy of tutorial.map in your maps directory
