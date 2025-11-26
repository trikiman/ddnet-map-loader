# DDNet Control Codebase Improvements

## 1. Map Change System Improvements

### Current Issues:
- Map change commands not working consistently
- Verification of map changes unreliable
- Limited error handling

### Solutions:
1. **Command Handling**:
   ```cpp
   bool change_map(SOCKET sock, const std::string& mapName) {
       // Try multiple command formats in sequence
       const std::vector<std::string> commands = {
           "change_map " + mapName,
           "sv_map " + mapName,
           "map " + mapName
       };
       
       for (const auto& cmd : commands) {
           if (send_command(sock, cmd)) {
               return verify_map_change(sock, mapName);
           }
       }
       return false;
   }
   ```

2. **Map Change Verification**:
   ```cpp
   bool verify_map_change(SOCKET sock, const std::string& expected_map) {
       for (int i = 0; i < 3; i++) {
           std::string current = get_current_map(sock);
           if (current == expected_map) return true;
           std::this_thread::sleep_for(std::chrono::seconds(1));
       }
       return false;
   }
   ```

## 2. File Management Enhancements

### Current Issues:
- No cleanup of old backups
- Basic map file validation
- Limited error handling for file operations

### Solutions:
1. **Backup Cleanup**:
   ```cpp
   void cleanup_old_backups(const fs::path& maps_dir) {
       const int MAX_BACKUPS = 10;
       std::vector<fs::path> backups;
       
       for (const auto& entry : fs::directory_iterator(maps_dir)) {
           if (entry.path().extension() == ".bak") {
               backups.push_back(entry.path());
           }
       }
       
       if (backups.size() > MAX_BACKUPS) {
           std::sort(backups.begin(), backups.end(), 
               [](const fs::path& a, const fs::path& b) {
                   return fs::last_write_time(a) < fs::last_write_time(b);
               });
           
           for (size_t i = 0; i < backups.size() - MAX_BACKUPS; ++i) {
               fs::remove(backups[i]);
           }
       }
   }
   ```

2. **Enhanced Map Validation**:
   ```cpp
   bool validate_map_file(const fs::path& mapPath) {
       std::ifstream file(mapPath, std::ios::binary);
       if (!file) return false;
       
       MapFileHeader header;
       file.read(reinterpret_cast<char*>(&header), sizeof(header));
       
       // Check magic number
       if (std::string(header.magic, 4) != "DATA" && 
           std::string(header.magic, 4) != "ATAD") {
           return false;
       }
       
       // Check version
       if (header.version < 1 || header.version > 5) {
           return false;
       }
       
       // Check size
       if (header.size <= 0 || header.size > 1024*1024*64) { // Max 64MB
           return false;
       }
       
       return true;
   }
   ```

## 3. Server Communication Improvements

### Current Issues:
- Limited logging
- Basic retry mechanism
- Generic error messages

### Solutions:
1. **Enhanced Logging**:
   ```cpp
   class Logger {
   public:
       enum Level { DEBUG, INFO, WARNING, ERROR };
       
       static void log(Level level, const std::string& message) {
           std::time_t now = std::time(nullptr);
           std::string timestamp = std::ctime(&now);
           timestamp.pop_back(); // Remove newline
           
           std::ofstream log_file("ddnet_control.log", std::ios::app);
           log_file << "[" << timestamp << "] [" 
                   << level_to_string(level) << "] " 
                   << message << std::endl;
       }
       
   private:
       static std::string level_to_string(Level level) {
           switch (level) {
               case DEBUG: return "DEBUG";
               case INFO: return "INFO";
               case WARNING: return "WARNING";
               case ERROR: return "ERROR";
               default: return "UNKNOWN";
           }
       }
   };
   ```

2. **Improved Command Retry Logic**:
   ```cpp
   bool send_command_with_retry(SOCKET sock, const std::string& command, 
                              int max_retries = 3, int delay_ms = 500) {
       std::string error;
       for (int attempt = 1; attempt <= max_retries; ++attempt) {
           if (send_command(sock, command)) {
               Logger::log(Logger::INFO, 
                   "Command sent successfully: " + command);
               return true;
           }
           
           error = "Attempt " + std::to_string(attempt) + 
                  " failed with error: " + std::to_string(WSAGetLastError());
           Logger::log(Logger::WARNING, error);
           
           if (attempt < max_retries) {
               std::this_thread::sleep_for(
                   std::chrono::milliseconds(delay_ms));
           }
       }
       
       Logger::log(Logger::ERROR, 
           "Failed to send command after " + 
           std::to_string(max_retries) + " attempts: " + command);
       return false;
   }
   ```

## 4. Integration Points

### Discord Bot Integration:
```cpp
class DiscordIntegration {
public:
    bool process_map_upload(const std::string& map_path) {
        // Validate map file
        if (!validate_map_file(map_path)) {
            return false;
        }
        
        // Connect to DDNet server
        ServerConnection conn;
        if (!conn.connect_with_retry()) {
            return false;
        }
        
        // Process map change
        return handle_map_replacement(conn.get_socket(), map_path);
    }
    
    std::vector<std::string> get_recent_maps() {
        fs::path maps_dir = fs::path(get_maps_directory());
        std::vector<std::string> recent_maps;
        
        // Get all .map files
        std::vector<fs::path> map_files;
        for (const auto& entry : fs::directory_iterator(maps_dir)) {
            if (entry.path().extension() == ".map") {
                map_files.push_back(entry.path());
            }
        }
        
        // Sort by last modified time
        std::sort(map_files.begin(), map_files.end(),
            [](const fs::path& a, const fs::path& b) {
                return fs::last_write_time(a) > fs::last_write_time(b);
            });
        
        // Get last 20 maps
        for (size_t i = 0; i < std::min(size_t(20), map_files.size()); ++i) {
            recent_maps.push_back(map_files[i].filename().string());
        }
        
        return recent_maps;
    }
};

# Step 1

Read featureswork.md in the docs folder 

## Step 2

Describe what you learned from featureswork.md in the docs folder

### Step 3

Check the features in featurework.md for failures on the entire codebase

### Step 4

If there are checking all unit:

1. Sort the checking features descending by the number of failures, errors and warnings collected, focusing on the features with the most collected first. Only check the features with the most collected.
2. Work on fixing all the failures in that specific feature.
3. Check features again to ensure there are no more failures.
4. Continue to work on the checking, fixing any remaining failures or warnings.

## Next Steps

1. **Implement Changes**:
   - Start with map change system improvements
   - Add logging system
   - Enhance file management
   - Add Discord integration points

2. **Testing**:
   - Create unit tests for new functionality
   - Test map change reliability
   - Verify backup cleanup
   - Test Discord integration

3. **Documentation**:
   - Update code comments
   - Create API documentation
   - Document error codes and messages
   - Add usage examples

4. **Future Enhancements**:
   - Add web interface integration
   - Implement session tracking
   - Add map statistics
   - Create configuration system
