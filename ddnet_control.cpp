#include <iostream>
#include <fstream>
#include <string>
#include <vector>
#include <filesystem>
#include <chrono>
#include <ctime>
#include <algorithm>
#include <memory>
#include <thread>
#include <sstream>
#include <cstdio>
#include <winsock2.h>
#include <ws2tcpip.h>
#include <windows.h>
#include <shellapi.h>
#include <shlobj.h>
#include <shlwapi.h>
#include <objbase.h>

#pragma comment(lib, "ws2_32.lib")
#pragma comment(lib, "shell32.lib")
#pragma comment(lib, "advapi32.lib")
#pragma comment(lib, "ole32.lib")

namespace fs = std::filesystem;

// Undefine Windows macros that clash with enum names
#ifdef ERROR
#undef ERROR
#endif
#ifdef WARNING
#undef WARNING
#endif
#ifdef DEBUG
#undef DEBUG
#endif

// Logger class for consistent logging throughout the application
class Logger {
public:
    enum class Level {
        DEBUG,
        INFO,
        WARNING,
        ERROR
    };

    // Convenience aliases so existing calls like Logger::ERROR work
    static constexpr Level DEBUG = Level::DEBUG;
    static constexpr Level INFO = Level::INFO;
    static constexpr Level WARNING = Level::WARNING;
    static constexpr Level ERROR = Level::ERROR;

    static void log(Level level, const std::string& message) {
        std::string level_str;
        switch (level) {
            case Level::DEBUG:   level_str = "DEBUG"; break;
            case Level::INFO:    level_str = "INFO"; break;
            case Level::WARNING: level_str = "WARNING"; break;
            case Level::ERROR:   level_str = "ERROR"; break;
        }

        auto now = std::chrono::system_clock::now();
        auto time = std::chrono::system_clock::to_time_t(now);
        std::string timestamp = std::ctime(&time);
        timestamp = timestamp.substr(0, timestamp.length() - 1); // Remove newline

        std::string log_message = "[" + timestamp + "] [" + level_str + "] " + message;
        
        // Log to console
        if (level == Level::ERROR) {
            std::cerr << log_message << std::endl;
        } else {
            std::cout << log_message << std::endl;
        }

        // Log to file in %APPDATA%/DDNet/maps
        static std::ofstream log_file;
        if (!log_file.is_open()) {
            // Resolve %APPDATA%/DDNet/maps and ensure it exists
            char* appDataPath = nullptr; size_t alen = 0;
            std::string logPath = "ddnet_control.log"; // fallback
            if (_dupenv_s(&appDataPath, &alen, "APPDATA") == 0 && appDataPath) {
                try {
                    fs::path mapsPath = fs::path(appDataPath) / "DDNet" / "maps";
                    free(appDataPath); appDataPath = nullptr;
                    std::error_code ec;
                    if (!fs::exists(mapsPath, ec)) {
                        fs::create_directories(mapsPath, ec);
                    }
                    if (!ec) {
                        logPath = (mapsPath / "ddnet_control.log").string();
                    }
                } catch (...) {
                    if (appDataPath) free(appDataPath);
                }
            }
            log_file.open(logPath, std::ios::app);
        }
        if (log_file.is_open()) {
            log_file << log_message << std::endl;
            log_file.flush();
        }
    }

private:
    Logger() {} // Prevent instantiation
};

// RAII helper for Winsock initialization
class WsaSession {
public:
    bool ok;
    WsaSession() : ok(false) {
        WSADATA wsaData;
        if (WSAStartup(MAKEWORD(2,2), &wsaData) == 0) {
            ok = true;
        } else {
            ok = false;
        }
    }
    ~WsaSession() {
        if (ok) {
            WSACleanup();
        }
    }
};

struct MapInfo {
    std::string originalMap;    // Original map name before any replacements
    std::string backupPath;     // Path to original backup
    std::string ddnetPath;      // Path to new map being used for replacement
};

// Forward declarations
bool set_socket_timeout(SOCKET sock, int timeout_ms);
bool send_command(SOCKET sock, const std::string& command);
bool receive_responses(SOCKET sock, std::vector<std::string>& responses, int timeout_ms = 2000);
bool authenticate(SOCKET sock);
std::string get_current_map(SOCKET sock);
std::string get_maps_directory();
bool file_exists(const std::string& path);
std::string get_map_name(const std::string& path);
bool copy_map_to_server(const std::string& mapPath, SOCKET sock);
bool change_map(SOCKET sock, const std::string& mapName);
bool verify_hot_reload(SOCKET sock, const std::string& expected_map);
bool is_valid_map_file(const fs::path& mapPath, std::string& error);
bool replace_map(MapInfo& mapInfo, SOCKET sock);
bool restore_backup(SOCKET sock);
bool hot_reload_map(SOCKET sock);
SOCKET create_and_connect_socket();
void print_usage(const char* program_name);
bool verify_file_association();
bool verify_permissions(const std::string& path);

bool send_command(SOCKET sock, const std::string& command);
bool receive_responses(SOCKET sock, std::vector<std::string>& responses, int timeoutMs);
std::vector<std::string> get_responses(SOCKET sock, int maxResponses, int timeoutMs);

// ===== Helpers for lastmapname.txt handling =====
static std::string get_lastmap_file_path() {
    std::string mapsDir = get_maps_directory();
    if (mapsDir.empty()) return "";
    fs::path p = fs::path(mapsDir) / "lastmapname.txt";
    return p.string();
}

static bool parse_lastmap_line(const std::string& line, std::string& last_new_map, std::string& last_current_map) {
    // Format: "new_map"(current_map)
    size_t q1 = line.find('"');
    if (q1 == std::string::npos) return false;
    size_t q2 = line.find('"', q1 + 1);
    if (q2 == std::string::npos || q2 == q1 + 1) return false;
    size_t lpar = line.find('(', q2 + 1);
    size_t rpar = line.find(')', lpar + 1);
    if (lpar == std::string::npos || rpar == std::string::npos || rpar <= lpar + 1) return false;
    last_new_map = line.substr(q1 + 1, q2 - q1 - 1);
    last_current_map = line.substr(lpar + 1, rpar - lpar - 1);
    // trim spaces
    auto trim = [](std::string& s){
        if (s.empty()) return;
        s.erase(0, s.find_first_not_of(" \t\r\n"));
        if (!s.empty()) s.erase(s.find_last_not_of(" \t\r\n") + 1);
    };
    trim(last_new_map);
    trim(last_current_map);
    return !last_new_map.empty() && !last_current_map.empty();
}

static void read_lastmap(std::string& last_new_map, std::string& last_current_map) {
    last_new_map.clear();
    last_current_map.clear();
    std::string path = get_lastmap_file_path();
    if (path.empty()) return;
    std::ifstream f(path);
    if (!f.is_open()) return;
    std::string line;
    std::getline(f, line);
    parse_lastmap_line(line, last_new_map, last_current_map);
}

static bool write_lastmap(const std::string& new_map, const std::string& current_map) {
    std::string path = get_lastmap_file_path();
    if (path.empty()) return false;
    std::ofstream f(path, std::ios::trunc);
    if (!f.is_open()) return false;
    f << '"' << new_map << '"' << '(' << current_map << ')';
    return true;
}

static void clear_lastmap() {
    std::string path = get_lastmap_file_path();
    if (path.empty()) return;
    std::ofstream f(path, std::ios::trunc);
}

// Save backup info to a file
void save_backup_info(const MapInfo& mapInfo) {
    std::string configPath = fs::path(get_maps_directory()).parent_path().string() + "\\backup_info.txt";
    std::ofstream file(configPath);
    if (file.is_open()) {
        file << mapInfo.originalMap << std::endl;
        file << mapInfo.backupPath << std::endl;
        file.close();
    }
}

// Remove old backup files like "*_backup.map" from DDNet maps directory
// Policy: delete backups older than 14 days. Non-fatal on errors.
static void cleanup_old_backups(const fs::path& maps_dir) {
    try {
        if (maps_dir.empty() || !fs::exists(maps_dir) || !fs::is_directory(maps_dir)) {
            return;
        }

        const auto now = fs::file_time_type::clock::now();
        const auto max_age = std::chrono::hours(24 * 14); // 14 days

        for (const auto& entry : fs::directory_iterator(maps_dir)) {
            if (!entry.is_regular_file()) continue;
            const auto& p = entry.path();
            const std::string name = p.filename().string();
            if (p.extension() == ".map" && name.size() > 12 && name.rfind("_backup.map") == name.size() - 12) {
                std::error_code ec;
                auto ts = fs::last_write_time(p, ec);
                if (ec) {
                    Logger::log(Logger::WARNING, "Unable to read timestamp for: " + p.string());
                    continue;
                }
                if (now - ts > max_age) {
                    std::error_code rec;
                    fs::remove(p, rec);
                    if (!rec) {
                        Logger::log(Logger::INFO, "Removed old backup: " + p.string());
                    } else {
                        Logger::log(Logger::WARNING, "Failed to remove old backup: " + p.string() + " - " + rec.message());
                    }
                }
            }
        }
    } catch (const std::exception& e) {
        Logger::log(Logger::WARNING, std::string("cleanup_old_backups error: ") + e.what());
    }
}

// Load backup info from file
bool load_backup_info(MapInfo& mapInfo) {
    std::string configPath = fs::path(get_maps_directory()).parent_path().string() + "\\backup_info.txt";
    std::ifstream file(configPath);
    if (file.is_open()) {
        std::getline(file, mapInfo.originalMap);
        std::getline(file, mapInfo.backupPath);
        file.close();
        return !mapInfo.originalMap.empty() && !mapInfo.backupPath.empty();
    }
    return false;
}

// [Note: This is a truncated version for GitHub upload. Full source is 1624 lines.]
// The complete source code includes all socket communication, map validation,
// file operations, and main() function implementation.

int main(int argc, char* argv[]) {
    // Main application entry point
    // Full implementation handles command line arguments,
    // socket connections, and map file operations
    std::cout << "DDNet Map Loader v2.0.0" << std::endl;
    std::cout << "For complete source code, see the full ddnet_control.cpp file" << std::endl;
    return 0;
}