# App for Discord and DDNet Game Integration

This project creates a C++ application that connects to both Discord and DDNet game server, providing map management and session tracking functionality across multiple channels.

## Discord Bot Features

### 1. General Channel Features
- Map upload handling: Bot simulates double click when a map is uploaded
- Reaction system: Adds confirmation emoji when map processing is complete
- Interactive reactions: Re-processes map when emoji is clicked again
- Map listing command: !map shows last 20 maps in folder

#### Map List Format Example:
```
1034563956234272767_hui (17) 19:24-22-11-2024
1034563956234272767_hui (16) 14:12-22-11-2024
1034563956234272767_hui (15) 13:54-22-11-2024
123                          13:52-22-11-2024
1034563956234272767_hui (14) 18:56-21-11-2024
1034563956234272767_hui (5)  17:58-21-11-2024
1034563956234272767_hui (13) 13:58-21-11-2024
1034563956234272767_hui (12) 15:53-20-11-2024
1034563956234272767_hui (11) 19:10-19-11-2024
1034563956234272767_hui (9)  15:01-19-11-2024
1034563956234272767_hui (10) 13:23-19-11-2024
1034563956234272767_hui (8)  13:28-18-11-2024
1 (1)                        12:57-18-11-2024
1034563956234272767_hui (7)  16:10-13-11-2024
1034563956234272767_hui (6)  10:52-13-11-2024
1034563956234272767_hui (4)  09:13-13-11-2024
1                            03:44-13-11-2024
Ham5 map                     01:57-13-11-2024
1 (2)                        15:18-11-11-2024
1034563956234272767_hui (3)  14:57-11-11-2024
```

### 2. Message History Channel
Message format examples:
```
🤖 Discord bot connected successfully.
👋 '[D] Ʈ¥4ƙą_' has left the game
💬 triki: и стартани
🎮 '[D] Ʈ¥4ƙą_' entered and joined the game
ℹ️  '[D] Ʈ¥4ƙą_' joined team 2
```
Note: If link contains an image, bot will preview this image in channel.

### 3. Session Channel
Session information format:
```
📊 Session: ty4
─────────────────────────────
⏱  Duration:    13.0m
🕒  Start:       00:37:58
💬  Messages:    10
🎮  Teams:       0
─────────────────────────────
🔧 RCON Commands: 83 total
   • tele: 76 times
   • tele 1 0: 2 times
   • change_map 1: 1 times
   • change_map Rain: 1 times
   • help: 1 times
   • /cmdlist: 1 times
   • up: 1 times
─────────────────────────────
🗺 Regular Commands: 15 total
   • kill: 5 times
   • spec: 3 times
   • team: 3 times
   • emote: 2 times
   • whisper: 2 times
─────────────────────────────
🗺  Maps: total 3h
   Rain (1h34m) kefir (1h26m)
```
Note: Full command list can be found in 01-Idea.md

## Core Features

### 1. Run Any .map File on PC (Completed)
When you double-click any .map file on PC, it will hot_reload that map in game even if the application is not running.

#### Detailed Logic:
1. **File Association:**
   - .reg file tells Windows to run program when .map file (X) is double-clicked
   - Example: Double-click Linear.map (this becomes X)

2. **Map Management:**
   - LINEAR1: Original map stays where you double-clicked it
   - LINEAR2: Copy X to DDNet maps directory
   - LINEAR3: Copy that becomes current map (named as W)
   - W_backup: Original current map backed up

#### Example Flow:
Double-click Linear.map while Kobra.map is running:
- LINEAR1: Original Linear.map (where you clicked)
- LINEAR2: Linear.map (in DDNet maps folder)
- LINEAR3: Kobra.map (contains Linear map content)
- Original: Kobra_backup.map (original Kobra content)

#### Server Communication:
1. Connect to DDNet's ECON interface
2. Send sv_map to get current map name (W)
3. Create backup of W as W_backup.map
4. Replace W with LINEAR3 (content of X)
5. Send hot_reload command
6. Verify map changed successfully
7. Keep window open to show results

Result: You can hot_reload any map by double-clicking it, while keeping the original safe and preserving all copies.
Note: Additional backup logic details in backuplogic.md

### 2. Web Interface
- Drag and drop .map file on web interface to hot_reload map in game
- Progress bar shows map loading status
- Display last 20 maps from C:\Users\rust9\AppData\Roaming\DDNet\maps folder

## Technical Details

### Core Technologies
- **ECON Protocol**: External console for server control
- **TCP Sockets**: For reliable server communication
- **Discord API**: For bot integration
- **Windows API**: For file system operations

### References
- DDNet Source: https://github.com/ddnet
- Game Server: 127.0.0.1:8303
- Maps Directory: C:/Users/rust-/AppData/Roaming/DDNet/maps
