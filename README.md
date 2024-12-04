# DDNet Map Loader

A powerful tool for DDNet server administrators that allows hot-reloading maps while preserving player positions.

## 🌟 Features

- **Hot Reload**: Change maps without disconnecting players
- **Position Preservation**: Players stay in their exact positions after map change
- **Backup System**: Automatic backup of current map before changes
- **Double-Click Support**: Simply double-click any .map file to load it
- **Multi-Language**: Documentation in English, Russian, and German

## 📋 Requirements

- Windows operating system
- DDNet Server
- The tutorial.map file in your DDNet maps directory

## 📥 Installation

### Option 1: Download Pre-compiled Release (Recommended)
1. Go to [Releases](https://github.com/trikiman/ddnet-map-loader/releases/latest)
2. Download `ddnet-map-loader-v1.0.0.zip`
3. Extract to your desired location
4. Run `ddnet_control.exe`

### Option 2: Build from Source
1. Download and install [Visual Studio 2022](https://visualstudio.microsoft.com/downloads/)
2. Download `ddnet-map-loader-source-v1.0.0.zip` from [Releases](https://github.com/trikiman/ddnet-map-loader/releases/latest)
3. Extract the files
4. Run `compile.bat`

## 🚀 Quick Start

1. Copy `tutorial.map` to your DDNet maps directory:
   ```
   %AppData%\DDNet\maps\tutorial.map
   ```
2. Copy `myServerconfig.cfg` to your DDNet server's data directory
3. Start DDNet server with the config:
   ```
   DDNet-Server.exe -f myServerconfig.cfg
   ```
4. Double-click any .map file to hot-reload it!

## 📖 Documentation

- [English Guide](README_EN.md)
- [Russian Guide](README_RU.md)
- [German Guide](README_DE.md)

## 🛠️ Building from Source

1. Make sure you have Visual Studio 2022 installed
2. Clone this repository
3. Run `compile.bat`

## 🎮 Usage

### Method 1: Double-Click
Simply double-click any .map file to hot-reload it on your server.

### Method 2: Command Line
```batch
ddnet_control.exe <path_to_map> [options]
```

Options:
- `--restore`: Restore the previous map
- `--skip-backup`: Skip creating a backup

## 🔧 Server Configuration

The `myServerconfig.cfg` contains:
```
sv_name "DDNet Map Loader Server"
sv_port 8303
sv_max_clients 16
sv_rcon_password "test123"
sv_rcon_mod_password "test123"
ec_port 8303
ec_password "test123"
ec_bindaddr "127.0.0.1"
sv_map "tutorial"
```

⚠️ Remember to change the default passwords in production!

## 📝 License

MIT License - feel free to use and modify as you wish!

## 🙏 Credits

- DDNet Team for the amazing game
- Icon from DDNet game assets
