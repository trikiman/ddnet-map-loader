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
#include <tlhelp32.h>
#include <shellapi.h>
#include <shlobj.h>
#include <shlwapi.h>
#include <objbase.h>
#include <cctype>

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
        
        // Log to file only (no console output for GUI app)
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
bool is_sync_types_command(int argc, char* argv[]);
std::string get_sync_types_mode(int argc, char* argv[]);
int run_sync_types_command(int argc, char* argv[]);
void trigger_background_testing_sync_if_due();

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

bool set_socket_timeout(SOCKET sock, int timeoutMs) {
    // Set send timeout
    DWORD timeout = timeoutMs;
    if (setsockopt(sock, SOL_SOCKET, SO_SNDTIMEO, (char*)&timeout, sizeof(timeout)) != 0) {
        // std::cout << "Failed to set send timeout: " << WSAGetLastError() << std::endl;
        return false;
    }
    
    // Set receive timeout
    if (setsockopt(sock, SOL_SOCKET, SO_RCVTIMEO, (char*)&timeout, sizeof(timeout)) != 0) {
        // std::cout << "Failed to set receive timeout: " << WSAGetLastError() << std::endl;
        return false;
    }
    
    return true;
}

std::vector<std::string> split_string(const std::string& str, char delim) {
    std::vector<std::string> tokens;
    std::string token;
    std::istringstream token_stream(str);
    while (std::getline(token_stream, token, delim)) {
        if (!token.empty()) {
            tokens.push_back(token);
        }
    }
    return tokens;
}

bool send_command(SOCKET sock, const std::string& command) {
    std::string cmd = command + "\n";
    if (send(sock, cmd.c_str(), cmd.length(), 0) == SOCKET_ERROR) {
        // std::cerr << "Failed to send command: " << WSAGetLastError() << std::endl;
        return false;
    }
    return true;
}

bool receive_responses(SOCKET sock, std::vector<std::string>& responses, int timeout_ms) {
    const int BUFFER_SIZE = 4096;
    char buffer[BUFFER_SIZE];
    std::string accumulated_data;
    
    // Set socket timeout
    if (!set_socket_timeout(sock, timeout_ms)) {
        return false;
    }

    while (true) {
        int bytes_received = recv(sock, buffer, BUFFER_SIZE - 1, 0);
        if (bytes_received == SOCKET_ERROR) {
            int error = WSAGetLastError();
            if (error == WSAETIMEDOUT) {
                break;  // Timeout is expected and not an error
            }
            // std::cerr << "Error receiving data: " << error << std::endl;
            return false;
        }
        if (bytes_received == 0) {
            // std::cerr << "Connection closed by server" << std::endl;
            return false;
        }

        buffer[bytes_received] = '\0';
        accumulated_data += buffer;

        // Check if we've received complete responses
        size_t pos;
        while ((pos = accumulated_data.find('\n')) != std::string::npos) {
            std::string line = accumulated_data.substr(0, pos);
            if (!line.empty() && line != "> ") {  // Skip empty lines and prompts
                responses.push_back(line);
            }
            accumulated_data.erase(0, pos + 1);
        }

        // If we have responses and the remaining data ends with a prompt,
        // we can assume we're done
        if (!responses.empty() && accumulated_data == "> ") {
            break;
        }
    }

    return !responses.empty();
}

// === Econ password resolution =============================================
// `ddnet_control.exe` connects to the DDNet server's external console (econ)
// over TCP on `ec_port`. The password it sends is therefore `ec_password`,
// not `sv_rcon_password` (which is the in-game F2 RCON, a different channel).
//
// Resolution order (first non-empty wins):
//   1. DDNETCONTROL_ECON_PASSWORD environment variable
//   2. `econ_password=...` in `ddnet_control.cfg` next to the EXE
//   3. `%APPDATA%\DDNet\autoexec_server.cfg` (USERDIR autoexec — overrides
//      anything set in myServerConfig.cfg via `exec` chain)
//   4. running DDNet-Server.exe `data/myServerConfig.cfg`
//   5. running DDNet-Server.exe `data/autoexec_server.cfg`
//   6. Hardcoded fallback "test123" (with a WARNING log)
//
// Within a single file, the LAST `ec_password` line wins, matching DDNet's
// own "later command overrides" semantics.
//
// The chosen source (never the password value itself) is logged once per
// process invocation.

static std::string read_file_to_string(const std::wstring& path) {
    std::ifstream ifs(path, std::ios::binary);
    if (!ifs) return std::string();
    std::ostringstream ss;
    ss << ifs.rdbuf();
    return ss.str();
}

// Find the LAST `ec_password "value"` (or unquoted) line in a DDNet cfg file.
// Returns empty if absent. Comment-aware (`#`, `//`).
static std::string parse_last_ec_password(const std::wstring& cfg_path) {
    std::string content = read_file_to_string(cfg_path);
    if (content.empty()) return std::string();
    std::istringstream is(content);
    std::string line;
    const std::string key = "ec_password";
    std::string last_value;
    while (std::getline(is, line)) {
        if (!line.empty() && line.back() == '\r') line.pop_back();
        size_t first = line.find_first_not_of(" \t");
        if (first == std::string::npos) continue;
        if (line[first] == '#') continue;
        if (line[first] == '/' && first + 1 < line.size() && line[first + 1] == '/') continue;
        size_t kp = line.find(key, first);
        if (kp == std::string::npos) continue;
        // Word-boundary check on the left
        if (kp > 0) {
            unsigned char prev = static_cast<unsigned char>(line[kp - 1]);
            if (std::isalnum(prev) || prev == '_') continue;
        }
        size_t after = kp + key.size();
        // Require whitespace immediately after the key (avoids matching e.g. `ec_password_alt`)
        if (after >= line.size() || (line[after] != ' ' && line[after] != '\t')) continue;
        while (after < line.size() && (line[after] == ' ' || line[after] == '\t')) ++after;
        if (after >= line.size()) continue;
        if (line[after] == '"') {
            size_t end = line.find('"', after + 1);
            if (end != std::string::npos) {
                last_value = line.substr(after + 1, end - after - 1);
            }
        } else {
            size_t end = line.find_first_of(" \t", after);
            if (end == std::string::npos) end = line.size();
            last_value = line.substr(after, end - after);
        }
    }
    return last_value;
}

// Find the directory of a running `DDNet-Server.exe` (if any). Empty otherwise.
static std::wstring find_running_ddnet_server_dir() {
    HANDLE snap = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0);
    if (snap == INVALID_HANDLE_VALUE) return std::wstring();
    PROCESSENTRY32W pe{};
    pe.dwSize = sizeof(pe);
    std::wstring result;
    if (Process32FirstW(snap, &pe)) {
        do {
            if (_wcsicmp(pe.szExeFile, L"DDNet-Server.exe") == 0) {
                HANDLE proc = OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, FALSE, pe.th32ProcessID);
                if (proc) {
                    wchar_t buf[MAX_PATH] = {};
                    DWORD size = MAX_PATH;
                    if (QueryFullProcessImageNameW(proc, 0, buf, &size)) {
                        std::wstring full(buf);
                        size_t slash = full.find_last_of(L"\\/");
                        if (slash != std::wstring::npos) result = full.substr(0, slash);
                    }
                    CloseHandle(proc);
                    if (!result.empty()) break;
                }
            }
        } while (Process32NextW(snap, &pe));
    }
    CloseHandle(snap);
    return result;
}

// Directory of our own EXE.
static std::wstring get_own_dir() {
    wchar_t buf[MAX_PATH] = {};
    DWORD len = GetModuleFileNameW(nullptr, buf, MAX_PATH);
    if (len == 0) return std::wstring();
    std::wstring full(buf);
    size_t slash = full.find_last_of(L"\\/");
    if (slash != std::wstring::npos) return full.substr(0, slash);
    return std::wstring();
}

// %APPDATA%\DDNet (DDNet's USERDIR on Windows).
static std::wstring get_userdir_dir() {
    wchar_t* appdata = nullptr;
    HRESULT hr = SHGetKnownFolderPath(FOLDERID_RoamingAppData, 0, nullptr, &appdata);
    std::wstring result;
    if (SUCCEEDED(hr) && appdata) {
        result.assign(appdata);
        result += L"\\DDNet";
    }
    if (appdata) CoTaskMemFree(appdata);
    return result;
}

// Read a `key=value` (or `key = "value"`) entry from a simple cfg file.
static std::string read_kv_config(const std::wstring& path, const std::string& key) {
    std::string content = read_file_to_string(path);
    if (content.empty()) return std::string();
    std::istringstream is(content);
    std::string line;
    while (std::getline(is, line)) {
        if (!line.empty() && line.back() == '\r') line.pop_back();
        size_t first = line.find_first_not_of(" \t");
        if (first == std::string::npos) continue;
        if (line[first] == '#') continue;
        if (line[first] == '/' && first + 1 < line.size() && line[first + 1] == '/') continue;
        size_t eq = line.find('=', first);
        if (eq == std::string::npos) continue;
        std::string k = line.substr(first, eq - first);
        size_t kend = k.find_last_not_of(" \t");
        if (kend != std::string::npos) k.erase(kend + 1);
        if (k != key) continue;
        std::string v = line.substr(eq + 1);
        size_t vstart = v.find_first_not_of(" \t");
        v = (vstart == std::string::npos) ? std::string() : v.substr(vstart);
        size_t vend = v.find_last_not_of(" \t");
        if (vend != std::string::npos) v.erase(vend + 1);
        if (v.size() >= 2 && v.front() == '"' && v.back() == '"') v = v.substr(1, v.size() - 2);
        return v;
    }
    return std::string();
}

static std::string g_econ_password_cache;
static bool g_econ_password_resolved = false;

static const std::string& resolve_econ_password() {
    if (g_econ_password_resolved) return g_econ_password_cache;
    g_econ_password_resolved = true;

    // 1. Environment variable
    {
        char buf[512] = {};
        DWORD got = GetEnvironmentVariableA("DDNETCONTROL_ECON_PASSWORD", buf, (DWORD)sizeof(buf));
        if (got > 0 && got < sizeof(buf)) {
            g_econ_password_cache.assign(buf, got);
            Logger::log(Logger::INFO, "Econ password source: env DDNETCONTROL_ECON_PASSWORD");
            return g_econ_password_cache;
        }
    }

    // 2. ddnet_control.cfg next to the EXE
    {
        std::wstring own = get_own_dir();
        if (!own.empty()) {
            std::wstring cfg = own + L"\\ddnet_control.cfg";
            std::string pw = read_kv_config(cfg, "econ_password");
            if (!pw.empty()) {
                g_econ_password_cache = pw;
                Logger::log(Logger::INFO, "Econ password source: ddnet_control.cfg");
                return g_econ_password_cache;
            }
        }
    }

    // 3. USERDIR autoexec_server.cfg (last `ec_password` line wins).
    //    DDNet executes this from %APPDATA%\DDNet on startup; any value here
    //    overrides values set earlier by `exec myServerconfig.cfg`.
    {
        std::wstring userdir = get_userdir_dir();
        if (!userdir.empty()) {
            std::wstring cfg = userdir + L"\\autoexec_server.cfg";
            std::string pw = parse_last_ec_password(cfg);
            if (!pw.empty()) {
                g_econ_password_cache = pw;
                Logger::log(Logger::INFO, "Econ password source: %APPDATA%\\DDNet\\autoexec_server.cfg");
                return g_econ_password_cache;
            }
        }
    }

    // 4 & 5. Auto-detect from the running DDNet-Server.exe install dir.
    {
        std::wstring serverDir = find_running_ddnet_server_dir();
        if (!serverDir.empty()) {
            std::wstring cfg = serverDir + L"\\data\\myServerConfig.cfg";
            std::string pw = parse_last_ec_password(cfg);
            if (!pw.empty()) {
                g_econ_password_cache = pw;
                Logger::log(Logger::INFO, "Econ password source: running DDNet-Server.exe data/myServerConfig.cfg");
                return g_econ_password_cache;
            }
            std::wstring cfg2 = serverDir + L"\\data\\autoexec_server.cfg";
            pw = parse_last_ec_password(cfg2);
            if (!pw.empty()) {
                g_econ_password_cache = pw;
                Logger::log(Logger::INFO, "Econ password source: running DDNet-Server.exe data/autoexec_server.cfg");
                return g_econ_password_cache;
            }
        }
    }

    // 6. Hardcoded fallback
    g_econ_password_cache = "test123";
    Logger::log(Logger::WARNING,
                "Econ password source: hardcoded fallback (test123). "
                "Set DDNETCONTROL_ECON_PASSWORD or place ddnet_control.cfg "
                "(econ_password=...) next to the EXE if your server uses a different password.");
    return g_econ_password_cache;
}

bool authenticate(SOCKET sock) {
    // Send password immediately without waiting
    const std::string& pw = resolve_econ_password();
    send_command(sock, pw + "\n");

    // Wait for response with shorter timeout
    auto responses = get_responses(sock, 2, 500); // Reduced maxResponses to 2 and timeout to 500ms
    
    // Quick check for success
    for (const auto& response : responses) {
        if (response.find("Authentication successful") != std::string::npos) {
            return true;
        }
    }
    
    return false;
}

std::string get_current_map(SOCKET sock) {
    // std::cout << "\n=== Starting Map Query ===" << std::endl;
    // std::cout << "Sending sv_map command..." << std::endl;
    
    if (!send_command(sock, "sv_map")) {
        return "";
    }

    std::vector<std::string> responses;
    if (!receive_responses(sock, responses)) {
        return "";
    }

    // Find the response containing the map name
    std::string response;
    for (const auto& r : responses) {
        if (r.find("config: Value:") != std::string::npos) {
            response = r;
            break;
        }
    }

    // std::cout << "Response: " << response << std::endl;
    // std::cout << "\n";

    // Extract map name from response
    size_t valuePos = response.find("Value:");
    if (valuePos != std::string::npos) {
        // Get everything after "Value: "
        std::string mapName = response.substr(valuePos + 7);
        // Trim whitespace
        mapName.erase(0, mapName.find_first_not_of(" \t\r\n"));
        mapName.erase(mapName.find_last_not_of(" \t\r\n") + 1);
        return mapName;
    }

    return "";
}

// Server communication configuration
struct ServerConfig {
    static constexpr int DEFAULT_TIMEOUT_MS = 2000;
    static constexpr int MAX_RETRIES = 3;
    static constexpr int RETRY_DELAY_MS = 500;
    static constexpr int CONNECTION_TIMEOUT_MS = 5000;
};

class ServerConnection {
    SOCKET sock;
    bool connected;
    int timeout_ms;
    int retries;

public:
    ServerConnection() : sock(INVALID_SOCKET), connected(false), 
                        timeout_ms(ServerConfig::DEFAULT_TIMEOUT_MS),
                        retries(ServerConfig::MAX_RETRIES) {}

    bool connect_with_retry() {
        for (int attempt = 1; attempt <= retries; ++attempt) {
            sock = create_and_connect_socket();
            if (sock != INVALID_SOCKET) {
                if (set_socket_timeout(sock, timeout_ms)) {
                    connected = true;
                    return true;
                }
                closesocket(sock);
            }
            
            // std::cerr << "Connection attempt " << attempt << " failed. ";
            if (attempt < retries) {
                // std::cerr << "Retrying in " << ServerConfig::RETRY_DELAY_MS << "ms..." << std::endl;
                std::this_thread::sleep_for(std::chrono::milliseconds(ServerConfig::RETRY_DELAY_MS));
            }
        }
        return false;
    }

    bool send_command_with_retry(const std::string& command) {
        for (int attempt = 1; attempt <= retries; ++attempt) {
            if (send_command(sock, command)) {
                return true;
            }
            
            // std::cerr << "Send attempt " << attempt << " failed. ";
            if (attempt < retries) {
                // std::cerr << "Retrying..." << std::endl;
                std::this_thread::sleep_for(std::chrono::milliseconds(ServerConfig::RETRY_DELAY_MS));
            }
        }
        return false;
    }

    bool receive_with_retry(std::vector<std::string>& responses) {
        for (int attempt = 1; attempt <= retries; ++attempt) {
            if (receive_responses(sock, responses, timeout_ms)) {
                return true;
            }
            
            // std::cerr << "Receive attempt " << attempt << " failed. ";
            if (attempt < retries) {
                // std::cerr << "Retrying..." << std::endl;
                std::this_thread::sleep_for(std::chrono::milliseconds(ServerConfig::RETRY_DELAY_MS));
            }
        }
        return false;
    }

    void set_timeout(int ms) {
        timeout_ms = ms;
        if (connected) {
            set_socket_timeout(sock, timeout_ms);
        }
    }

    void set_retries(int count) {
        retries = count;
    }

    SOCKET get_socket() const {
        return sock;
    }

    void disconnect() {
        if (sock != INVALID_SOCKET) {
            closesocket(sock);
            sock = INVALID_SOCKET;
            connected = false;
        }
    }

    ~ServerConnection() {
        disconnect();
    }
};

bool hot_reload_map(SOCKET sock) {
    ServerConnection conn;
    if (!conn.connect_with_retry()) {
        // std::cerr << "Failed to establish server connection" << std::endl;
        return false;
    }

    if (!conn.send_command_with_retry("hot_reload")) {
        // std::cerr << "Failed to send hot_reload command" << std::endl;
        return false;
    }

    std::vector<std::string> responses;
    if (!conn.receive_with_retry(responses)) {
        // std::cerr << "Failed to receive response for hot_reload" << std::endl;
        return false;
    }

    return true;
}

bool verify_hot_reload(SOCKET sock, const std::string& expected_map) {
    // For hot reload, the map name doesn't change, we just need to verify
    // that the server is still responsive after the reload
    const int MAX_RETRIES = 3;
    const int RETRY_DELAY_MS = 500;

    for (int attempt = 1; attempt <= MAX_RETRIES; attempt++) {
        std::string current_map = get_current_map(sock);
        
        if (current_map.empty()) {
            // std::cerr << "Attempt " << attempt << ": Failed to get current map" << std::endl;
        } else {
            // For hot reload, we just need to verify the server is responsive
            // std::cout << "Hot reload verification successful!" << std::endl;
            return true;
        }

        if (attempt < MAX_RETRIES) {
            // std::cout << "Retry " << attempt + 1 << "/" << MAX_RETRIES << std::endl;
            std::this_thread::sleep_for(std::chrono::milliseconds(RETRY_DELAY_MS));
        }
    }

    // std::cerr << "Failed to verify server response after " << MAX_RETRIES << " attempts" << std::endl;
    return false;
}

bool is_valid_map_file(const fs::path& mapPath, std::string& error) {
    try {
        // First check if file exists
        if (!fs::exists(mapPath)) {
            error = "Map file does not exist: " + mapPath.string();
            return false;
        }

        // Check if it's a regular file
        if (!fs::is_regular_file(mapPath)) {
            error = "Path is not a regular file: " + mapPath.string();
            return false;
        }

        // Try to get file size
        std::error_code ec;
        auto fileSize = fs::file_size(mapPath, ec);
        if (ec) {
            error = "Cannot read file size: " + ec.message();
            return false;
        }

        // Check if file is empty
        if (fileSize == 0) {
            error = "Map file is empty";
            return false;
        }

        // Try to open and read first few bytes
        std::ifstream file(mapPath, std::ios::binary);
        if (!file.is_open()) {
            error = "Cannot open map file: " + mapPath.string();
            return false;
        }

        // Read first few bytes to verify it's a valid map file
        char header[8];
        if (!file.read(header, sizeof(header))) {
            error = "Cannot read map file header";
            return false;
        }

        return true;
    }
    catch (const std::exception& e) {
        error = std::string("Error validating map file: ") + e.what();
        return false;
    }
}

std::string get_maps_directory() {
    char* appDataPath;
    size_t len;
    errno_t err = _dupenv_s(&appDataPath, &len, "APPDATA");
    if (err != 0 || appDataPath == nullptr) {
        return "";
    }

    fs::path mapsPath = fs::path(appDataPath) / "DDNet" / "maps";
    free(appDataPath);

    if (!fs::exists(mapsPath)) {
        // Do not fail; caller may want to create it during preflight
        return mapsPath.string();
    }

    return mapsPath.string();
}

// Ensure a directory exists (create if missing). Returns full path string or empty on error.
static std::string ensure_directory(const fs::path& p) {
    try {
        std::error_code ec;
        if (!fs::exists(p, ec)) {
            if (!fs::create_directories(p, ec) && ec) {
                Logger::log(Logger::ERROR, "Failed to create directory: " + p.string() + " - " + ec.message());
                return "";
            }
        } else if (!fs::is_directory(p)) {
            Logger::log(Logger::ERROR, "Path exists but is not a directory: " + p.string());
            return "";
        }
        return p.string();
    } catch (const std::exception& e) {
        Logger::log(Logger::ERROR, std::string("ensure_directory exception: ") + e.what());
        return "";
    }
}

static std::string get_or_create_maps_directory() {
    std::string maps = get_maps_directory();
    if (maps.empty()) return ""; // APPDATA missing
    return ensure_directory(fs::path(maps));
}

static std::string get_or_create_backups_directory() {
    std::string maps = get_or_create_maps_directory();
    if (maps.empty()) return "";
    fs::path backups = fs::path(maps) / "backups";
    return ensure_directory(backups);
}

// Timestamp as YYYYMMDD-HHMMSS
static std::string make_timestamp() {
    using namespace std::chrono;
    auto now = system_clock::now();
    std::time_t t = system_clock::to_time_t(now);
    std::tm tm_buf{};
    localtime_s(&tm_buf, &t);
    char buf[32];
    std::snprintf(buf, sizeof(buf), "%04d%02d%02d-%02d%02d%02d",
                  tm_buf.tm_year + 1900, tm_buf.tm_mon + 1, tm_buf.tm_mday,
                  tm_buf.tm_hour, tm_buf.tm_min, tm_buf.tm_sec);
    return std::string(buf);
}

// Create marker like "Tutorial map not exist.map", append (1), (2), ... if exists
static fs::path next_marker_path(const fs::path& dir, const std::string& baseNameWithExt) {
    fs::path base = dir / baseNameWithExt; // e.g., backups / "Tutorial map not exist.map"
    if (!fs::exists(base)) return base;
    for (int i = 1; i < 1000; ++i) {
        std::string stem = fs::path(baseNameWithExt).stem().string();
        std::string ext = fs::path(baseNameWithExt).extension().string();
        fs::path cand = dir / (stem + " (" + std::to_string(i) + ")" + ext);
        if (!fs::exists(cand)) return cand;
    }
    return base; // Fallback
}

// Simple change_map implementation
bool change_map(SOCKET sock, const std::string& mapName) {
    std::string cmd = std::string("change_map ") + mapName;
    if (!send_command(sock, cmd)) return false;
    // Brief wait and ping status
    Sleep(200);
    (void)send_command(sock, "status");
    return true; // Assume success if ECON is responsive
}

bool setupFileAssociation() {
    // Build command string with current exe path and quoted "%1"
    wchar_t exePath[MAX_PATH] = {0};
    DWORD len = GetModuleFileNameW(NULL, exePath, MAX_PATH);
    if (len == 0 || len >= MAX_PATH) {
        Logger::log(Logger::ERROR, "GetModuleFileNameW failed when setting up association");
        return false;
    }

    std::wstring command = L"\""; // opening quote
    command += exePath;
    command += L"\" \"%1\""; // space then quoted %1

    // Use HKCU\Software\Classes to avoid admin requirement
    HKEY hkey;
    // 1) Set .map default value to our ProgID
    if (RegCreateKeyExW(HKEY_CURRENT_USER, L"Software\\Classes\\.map", 0, NULL,
                        REG_OPTION_NON_VOLATILE, KEY_WRITE, NULL, &hkey, NULL) != ERROR_SUCCESS) {
        Logger::log(Logger::ERROR, "Failed to open/create HKCU\\Software\\Classes\\.map");
        return false;
    }
    const wchar_t* progId = L"DDNetMapFile";
    if (RegSetValueExW(hkey, NULL, 0, REG_SZ, (const BYTE*)progId, (DWORD)((wcslen(progId) + 1) * sizeof(wchar_t))) != ERROR_SUCCESS) {
        Logger::log(Logger::ERROR, "Failed to set ProgID for .map");
        RegCloseKey(hkey);
        return false;
    }
    RegCloseKey(hkey);

    // 2) Set command under ProgID
    if (RegCreateKeyExW(HKEY_CURRENT_USER, L"Software\\Classes\\DDNetMapFile\\shell\\open\\command", 0, NULL,
                        REG_OPTION_NON_VOLATILE, KEY_WRITE, NULL, &hkey, NULL) != ERROR_SUCCESS) {
        Logger::log(Logger::ERROR, "Failed to create open\\command key for DDNetMapFile");
        return false;
    }
    if (RegSetValueExW(hkey, NULL, 0, REG_SZ, (const BYTE*)command.c_str(), (DWORD)((command.size() + 1) * sizeof(wchar_t))) != ERROR_SUCCESS) {
        Logger::log(Logger::ERROR, "Failed to set open command for DDNetMapFile");
        RegCloseKey(hkey);
        return false;
    }
    RegCloseKey(hkey);

    // 3) Optional: set a friendly name and default icon (non-blocking if fails)
    if (RegCreateKeyExW(HKEY_CURRENT_USER, L"Software\\Classes\\DDNetMapFile", 0, NULL,
                        REG_OPTION_NON_VOLATILE, KEY_WRITE, NULL, &hkey, NULL) == ERROR_SUCCESS) {
        const wchar_t* friendly = L"DDNet Map File";
        RegSetValueExW(hkey, NULL, 0, REG_SZ, (const BYTE*)friendly, (DWORD)((wcslen(friendly) + 1) * sizeof(wchar_t)));
        RegCloseKey(hkey);
    }
    if (RegCreateKeyExW(HKEY_CURRENT_USER, L"Software\\Classes\\DDNetMapFile\\DefaultIcon", 0, NULL,
                        REG_OPTION_NON_VOLATILE, KEY_WRITE, NULL, &hkey, NULL) == ERROR_SUCCESS) {
        // Use project icon if present; fall back to exe icon automatically
        // Note: change below if you want to force ddnet-unstable.ico
        std::wstring iconValue = L"\""; iconValue += exePath; iconValue += L"\",0";
        RegSetValueExW(hkey, NULL, 0, REG_SZ, (const BYTE*)iconValue.c_str(), (DWORD)((iconValue.size() + 1) * sizeof(wchar_t)));
        RegCloseKey(hkey);
    }

    Logger::log(Logger::INFO, "File association updated for current user (.map -> ddnet_control.exe)");
    Logger::log(Logger::INFO, "Command: " + std::string("(wide)") );
    return true;
}

bool file_exists(const std::string& path) {
    return fs::exists(path);
}

std::string get_map_name(const std::string& path) {
    return fs::path(path).stem().string();
}

// DDNet map file header structure
struct MapFileHeader {
    char magic[4];       // "DATA" or "ATAD"
    int32_t version;     // Map version
    int32_t size;        // Size of the map data
    int32_t swaplen;     // Size of data to swap
    int32_t num_item_types;
    int32_t num_items;
    int32_t num_raw_data;
    int32_t item_size;
    int32_t data_size;
};

bool validate_map_file(const std::string& mapPath) {
    std::ifstream file(mapPath, std::ios::binary);
    if (!file) {
        // std::cerr << "Cannot open map file: " << mapPath << std::endl;
        return false;
    }

    MapFileHeader header;
    file.read(reinterpret_cast<char*>(&header), sizeof(header));

    if (!file) {
        // std::cerr << "Failed to read map header: " << mapPath << std::endl;
        return false;
    }

    // Check magic number
    std::string magic(header.magic, 4);
    if (magic != "DATA" && magic != "ATAD") {
        // std::cerr << "Invalid map file format: " << mapPath << std::endl;
        return false;
    }

    // Basic sanity checks
    if (header.size <= 0 || header.size > 1024*1024*64) {  // Max 64MB
        // std::cerr << "Invalid map size: " << header.size << " bytes" << std::endl;
        return false;
    }

    return true;
}

// File locking mechanism
class FileLock {
    HANDLE fileHandle;
    std::string filePath;

public:
    FileLock(const std::string& path) : filePath(path), fileHandle(INVALID_HANDLE_VALUE) {}

    bool acquire() {
        fileHandle = CreateFileA(
            filePath.c_str(),
            GENERIC_READ | GENERIC_WRITE,
            0,  // No sharing
            NULL,
            OPEN_EXISTING,
            FILE_ATTRIBUTE_NORMAL,
            NULL
        );

        if (fileHandle == INVALID_HANDLE_VALUE) {
            // std::cerr << "Failed to lock file: " << filePath << std::endl;
            return false;
        }
        return true;
    }

    void release() {
        if (fileHandle != INVALID_HANDLE_VALUE) {
            CloseHandle(fileHandle);
            fileHandle = INVALID_HANDLE_VALUE;
        }
    }

    ~FileLock() {
        release();
    }
};

bool copy_map_to_server(const std::string& mapPath, SOCKET sock) {
    try {
        // Validate map file first
        if (!validate_map_file(mapPath)) {
            // std::cerr << "Map validation failed" << std::endl;
            return false;
        }

        std::string mapsDir = get_maps_directory();
        if (mapsDir.empty()) {
            return false;
        }

        // Get current map name from server
        std::string currentMap = get_current_map(sock);
        if (currentMap.empty()) {
            // std::cerr << "Could not determine current map name" << std::endl;
            return false;
        }

        // Get map name without path
        std::string mapName = fs::path(mapPath).filename().string();
        fs::path targetPath = fs::path(mapsDir) / currentMap;
        std::string targetPathStr = targetPath.string() + ".map";

        // Create file lock
        FileLock lock(targetPathStr);
        if (!lock.acquire()) {
            // std::cerr << "Map file is currently in use" << std::endl;
            return false;
        }

        // Get target file size
        std::error_code ec;
        uintmax_t targetSize = fs::file_size(mapPath, ec);
        if (ec) {
            // std::cerr << "Failed to get source file size: " << ec.message() << std::endl;
            return false;
        }

        // std::cout << "\n=== Copying Map to Server ===" << std::endl;
        // std::cout << "Source map: " << mapPath << " (" << mapName << ")" << std::endl;
        // std::cout << "Target map: " << targetPathStr << " (" << currentMap << ")" << std::endl;

        // Check if source map exists
        if (!fs::exists(mapPath)) {
            // std::cerr << "Source map does not exist: " << mapPath << std::endl;
            return false;
        }

        // Try to copy with retries
        for (int attempt = 1; attempt <= 3; attempt++) {
            try {
                // If target exists, try to remove it first
                if (fs::exists(targetPath)) {
                    // std::cout << "Removing existing map..." << std::endl;
                    fs::remove(targetPath);
                }

                // Copy the new map
                fs::copy_file(mapPath, targetPath, fs::copy_options::overwrite_existing);
                
                // Verify the copy was successful
                if (!fs::exists(targetPath)) {
                    throw fs::filesystem_error("Map file not found after copy", targetPath, std::error_code());
                }

                // Verify file sizes match
                auto sourceSize = fs::file_size(mapPath);
                auto targetSize = fs::file_size(targetPath);
                if (sourceSize != targetSize) {
                    throw fs::filesystem_error(
                        "File size mismatch after copy: source=" + std::to_string(sourceSize) + 
                        ", target=" + std::to_string(targetSize),
                        targetPath, std::error_code());
                }

                // std::cout << "Successfully copied map file" << std::endl;
                return true;
            }
            catch (const fs::filesystem_error& e) {
                // std::cout << "Copy attempt " << attempt << " failed: " << e.what() << std::endl;
                if (attempt < 3) {
                    // std::cout << "Waiting before retry..." << std::endl;
                    std::this_thread::sleep_for(std::chrono::milliseconds(100)); // Reduced from 1000ms to 100ms
                }
            }
        }
        // std::cerr << "Failed to copy map after 3 attempts" << std::endl;
        return false;
    }
    catch (const std::exception& e) {
        // std::cerr << "Error copying map: " << e.what() << std::endl;
        return false;
    }
}

bool replace_map(MapInfo& mapInfo, SOCKET sock) {
    try {
        // Get current map name from server
        std::string serverMap = get_current_map(sock);
        if (serverMap.empty()) {
            // std::cerr << "Could not determine current map name" << std::endl;
            return false;
        }

        std::string mapsDir = get_maps_directory();
        if (mapsDir.empty()) {
            // std::cerr << "Could not find DDNet maps directory" << std::endl;
            return false;
        }

        // Set up paths
        fs::path backupPath = fs::path(mapsDir) / (serverMap + "_backup.map");
        fs::path currentMapPath = fs::path(mapsDir) / (serverMap + ".map");

        // std::cout << "\n=== Map Replacement Process ===" << std::endl;
        // std::cout << "Current server map: " << serverMap << std::endl;

        // Handle backup based on existence
        if (fs::exists(backupPath)) {
            // std::cout << "Found existing backup at: " << backupPath.string() << std::endl;
            mapInfo.backupPath = backupPath.string();
            mapInfo.originalMap = serverMap;
        } else {
            // Create original backup since it doesn't exist
            try {
                fs::copy_file(currentMapPath, backupPath, fs::copy_options::none);
                // std::cout << "Created backup at: " << backupPath.string() << std::endl;
                mapInfo.backupPath = backupPath.string();
                mapInfo.originalMap = serverMap;
                save_backup_info(mapInfo);
            }
            catch (const fs::filesystem_error& e) {
                // std::cerr << "Failed to create original backup: " << e.what() << std::endl;
                return false;
            }
        }

        // Copy new map to server's map location
        try {
            // std::cout << "\nCopying from: " << mapInfo.ddnetPath << std::endl;
            // std::cout << "Copying to: " << currentMapPath.string() << std::endl;
            fs::copy_file(mapInfo.ddnetPath, currentMapPath, fs::copy_options::overwrite_existing);
            // std::cout << "Successfully copied map to: " << currentMapPath.string() << std::endl;
        }
        catch (const fs::filesystem_error& e) {
            // std::cerr << "Failed to copy map: " << e.what() << std::endl;
            return false;
        }

        // Send hot reload command
        if (!send_command(sock, "hot_reload")) {
            // std::cerr << "Failed to send reload command" << std::endl;
            return false;
        }

        // Verify the hot reload
        if (!verify_hot_reload(sock, get_map_name(mapInfo.ddnetPath))) {
            // std::cerr << "Failed to verify hot reload" << std::endl;
            return false;
        }

        return true;
    }
    catch (const std::exception& e) {
        // std::cerr << "Error in replace_map: " << e.what() << std::endl;
        return false;
    }
}

bool restore_backup(SOCKET sock) {
    try {
        std::string serverMap = get_current_map(sock);
        if (serverMap.empty()) {
            // std::cerr << "Could not determine current map name" << std::endl;
            return false;
        }

        std::string mapsDir = get_maps_directory();
        if (mapsDir.empty()) {
            // std::cerr << "Could not find DDNet maps directory" << std::endl;
            return false;
        }

        // Setup paths - use server's current map name
        fs::path currentMapPath = fs::path(mapsDir) / (serverMap + ".map");
        fs::path backupPath = fs::path(mapsDir) / (serverMap + "_backup.map");

        // std::cout << "\n=== Map Restore Process ===" << std::endl;
        // std::cout << "Current server map: " << serverMap << std::endl;
        // std::cout << "Original backup: " << backupPath.string() << std::endl;

        // Check if original backup exists
        if (!fs::exists(backupPath)) {
            // std::cerr << "Original backup not found: " << backupPath.string() << std::endl;
            return false;
        }

        // Copy backup back to current map
        try {
            fs::copy_file(backupPath, currentMapPath, fs::copy_options::overwrite_existing);
            // std::cout << "Successfully restored from original backup" << std::endl;
        }
        catch (const fs::filesystem_error& e) {
            // std::cerr << "Failed to restore from backup: " << e.what() << std::endl;
            return false;
        }

        // Send reload command
        if (!send_command(sock, "hot_reload")) {
            // std::cerr << "Failed to send reload command" << std::endl;
            return false;
        }

        // Verify the hot reload using the original map name
        if (!verify_hot_reload(sock, serverMap)) {
            // std::cerr << "Failed to verify hot reload after restore" << std::endl;
            return false;
        }

        // std::cout << "Map restore completed successfully" << std::endl;
        return true;
    }
    catch (const std::exception& e) {
        // std::cerr << "Error in restore_backup: " << e.what() << std::endl;
        return false;
    }
}

bool is_server_running() {
    SOCKET test_sock = socket(AF_INET, SOCK_STREAM, 0);
    if (test_sock == INVALID_SOCKET) {
        return false;
    }

    sockaddr_in serverAddr;
    serverAddr.sin_family = AF_INET;
    serverAddr.sin_port = htons(8303);
    serverAddr.sin_addr.s_addr = inet_addr("127.0.0.1");

    // Try to connect with a short timeout
    u_long mode = 1;  // 1 to enable non-blocking
    ioctlsocket(test_sock, FIONBIO, &mode);

    connect(test_sock, (sockaddr*)&serverAddr, sizeof(serverAddr));

    fd_set write_fds;
    FD_ZERO(&write_fds);
    FD_SET(test_sock, &write_fds);

    timeval timeout;
    timeout.tv_sec = 1;
    timeout.tv_usec = 0;

    int result = select(0, NULL, &write_fds, NULL, &timeout);

    closesocket(test_sock);
    return result > 0;
}

SOCKET create_and_connect_socket() {
    // std::cout << "Connecting to DDNet server..." << std::endl;

    SOCKET sock = socket(AF_INET, SOCK_STREAM, 0);
    if (sock == INVALID_SOCKET) {
        // std::cerr << "Failed to create socket: " << WSAGetLastError() << std::endl;
        return INVALID_SOCKET;
    }

    // Set up server address
    sockaddr_in serverAddr;
    serverAddr.sin_family = AF_INET;
    serverAddr.sin_port = htons(8303);
    serverAddr.sin_addr.s_addr = inet_addr("127.0.0.1");

    // Set connection timeout
    if (!set_socket_timeout(sock, 5000)) {  // 5 second timeout
        closesocket(sock);
        return INVALID_SOCKET;
    }

    // Connect to server
    if (connect(sock, (sockaddr*)&serverAddr, sizeof(serverAddr)) == SOCKET_ERROR) {
        int error = WSAGetLastError();
        // std::cerr << "Failed to connect to server: ";
        switch (error) {
            case WSAECONNREFUSED:
                // std::cerr << "Connection refused (Is the server running?)";
                break;
            case WSAETIMEDOUT:
                // std::cerr << "Connection timed out";
                break;
            case WSAEHOSTUNREACH:
                // std::cerr << "Host unreachable";
                break;
            default:
                // std::cerr << "Error " << error;
                break;
        }
        // std::cerr << std::endl;
        closesocket(sock);
        return INVALID_SOCKET;
    }

    // std::cout << "Successfully connected to server" << std::endl;
    return sock;
}

bool is_restore_command(int argc, char* argv[]) {
    for (int i = 1; i < argc; i++) {
        if (std::string(argv[i]) == "--restore") {
            return true;
        }
    }
    return false;
}

bool is_setup_command(int argc, char* argv[]) {
    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "--setup") == 0) {
            return true;
        }
    }
    return false;
}

bool is_sync_types_command(int argc, char* argv[]) {
    for (int i = 1; i < argc; i++) {
        if (
            strcmp(argv[i], "--sync-types") == 0 ||
            strcmp(argv[i], "--sync-types-official") == 0 ||
            strcmp(argv[i], "--sync-types-testing") == 0
        ) {
            return true;
        }
    }
    return false;
}

std::string get_sync_types_mode(int argc, char* argv[]) {
    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "--sync-types-official") == 0) {
            return "official";
        }
        if (strcmp(argv[i], "--sync-types-testing") == 0) {
            return "testing";
        }
    }
    return "all";
}

static int run_hidden_process(const std::wstring& file, const std::wstring& parameters, const std::wstring& working_dir) {
    SHELLEXECUTEINFOW exec_info = { sizeof(exec_info) };
    exec_info.fMask = SEE_MASK_NOCLOSEPROCESS | SEE_MASK_FLAG_NO_UI;
    exec_info.lpVerb = L"open";
    exec_info.lpFile = file.c_str();
    exec_info.lpParameters = parameters.empty() ? nullptr : parameters.c_str();
    exec_info.lpDirectory = working_dir.empty() ? nullptr : working_dir.c_str();
    exec_info.nShow = SW_HIDE;

    if (!ShellExecuteExW(&exec_info)) {
        Logger::log(Logger::ERROR, "Failed to launch process");
        return -1;
    }

    if (exec_info.hProcess == nullptr) {
        return 0;
    }

    WaitForSingleObject(exec_info.hProcess, INFINITE);
    DWORD exit_code = 1;
    GetExitCodeProcess(exec_info.hProcess, &exit_code);
    CloseHandle(exec_info.hProcess);
    return static_cast<int>(exit_code);
}

int run_sync_types_command(int argc, char* argv[]) {
    wchar_t exe_path[MAX_PATH] = {0};
    DWORD len = GetModuleFileNameW(NULL, exe_path, MAX_PATH);
    if (len == 0 || len >= MAX_PATH) {
        Logger::log(Logger::ERROR, "GetModuleFileNameW failed for sync-types command");
        return 1;
    }

    fs::path exe_dir = fs::path(exe_path).parent_path();
    fs::path script_path = exe_dir / "tools" / "map_sync.py";
    fs::path venv_python = exe_dir / "venv" / "Scripts" / "python.exe";
    std::wstring working_dir = exe_dir.wstring();

    if (!fs::exists(script_path)) {
        Logger::log(Logger::ERROR, "Sync script not found: " + script_path.string());
        return 1;
    }

    const std::string mode = get_sync_types_mode(argc, argv);
    const std::wstring quoted_script = L"\"" + script_path.wstring() + L"\"";
    const std::wstring quoted_mode = std::wstring(mode.begin(), mode.end());
    // --register-with-server runs Phase 2's storage.cfg install + record_maps
    // INSERT OR IGNORE after a successful sync. Safe: no DELETE / UPDATE, rolling backup kept.
    const std::wstring script_args = quoted_script + L" --mode " + quoted_mode + L" --register-with-server";

    Logger::log(Logger::INFO, "Starting type/testing map sync (" + mode + ", register-with-server=on)");

    if (fs::exists(venv_python)) {
        int exit_code = run_hidden_process(venv_python.wstring(), script_args, working_dir);
        if (exit_code == 0) {
            Logger::log(Logger::INFO, "Sync process exited with code 0");
            return 0;
        }
        Logger::log(Logger::WARNING, "venv python sync launch failed with code " + std::to_string(exit_code) + ", falling back to system python");
    }

    int exit_code = run_hidden_process(L"cmd.exe", L"/c py -3 " + script_args, working_dir);
    if (exit_code == 0) {
        Logger::log(Logger::INFO, "Sync process exited with code 0");
        return 0;
    }
    Logger::log(Logger::WARNING, "py -3 sync launch failed with code " + std::to_string(exit_code) + ", falling back to python");

    exit_code = run_hidden_process(L"cmd.exe", L"/c python " + script_args, working_dir);
    Logger::log(exit_code == 0 ? Logger::INFO : Logger::ERROR, "Sync process exited with code " + std::to_string(exit_code));
    return exit_code == -1 ? 1 : exit_code;
}

// ---------------------------------------------------------------------------
// TRIG-04 / SAFE-06: auto-trigger testing-only sync after RCON map change.
//
// Fires a background `python tools/map_sync.py --mode testing --register-with-server`
// in a detached process so the map-change call site doesn't block on the sync.
//
// Debounced via a file marker %APPDATA%\DDNet\types\.ddnetcontrol-last-auto-sync:
// if the marker was touched within AUTO_SYNC_DEBOUNCE_SEC, this call is a no-op.
// Rapid-fire map changes therefore coalesce into one sync.
// ---------------------------------------------------------------------------
constexpr int AUTO_SYNC_DEBOUNCE_SEC = 60;

static fs::path auto_sync_marker_path() {
    const wchar_t* appdata = _wgetenv(L"APPDATA");
    if (!appdata) return {};
    return fs::path(appdata) / L"DDNet" / L"types" / L".ddnetcontrol-last-auto-sync";
}

static bool auto_sync_debounce_allows() {
    fs::path marker = auto_sync_marker_path();
    if (marker.empty()) return false;
    std::error_code ec;
    if (!fs::exists(marker, ec)) return true;
    auto last = fs::last_write_time(marker, ec);
    if (ec) return true;  // if we can't read the time, allow the sync
    auto now = decltype(last)::clock::now();
    auto age = std::chrono::duration_cast<std::chrono::seconds>(now - last).count();
    return age >= AUTO_SYNC_DEBOUNCE_SEC;
}

static void auto_sync_touch_marker() {
    fs::path marker = auto_sync_marker_path();
    if (marker.empty()) return;
    std::error_code ec;
    fs::create_directories(marker.parent_path(), ec);
    std::ofstream(marker) << "last auto-sync trigger\n";
}

// Fire-and-forget testing-only sync. Non-blocking: spawns a detached child
// process and returns. The child picks the same venv/system-python fallback
// as run_sync_types_command, and uses --register-with-server so Phase 2's
// safety-rail-protected DB writes fire after the sync.
void trigger_background_testing_sync_if_due() {
    if (!auto_sync_debounce_allows()) {
        Logger::log(Logger::INFO, "Auto-sync skipped (debounce — last run <" + std::to_string(AUTO_SYNC_DEBOUNCE_SEC) + "s ago)");
        return;
    }
    auto_sync_touch_marker();

    wchar_t exe_path[MAX_PATH] = {0};
    DWORD len = GetModuleFileNameW(NULL, exe_path, MAX_PATH);
    if (len == 0 || len >= MAX_PATH) {
        Logger::log(Logger::WARNING, "Auto-sync: GetModuleFileNameW failed; skipping");
        return;
    }
    fs::path exe_dir = fs::path(exe_path).parent_path();
    fs::path script_path = exe_dir / "tools" / "map_sync.py";
    fs::path venv_python = exe_dir / "venv" / "Scripts" / "python.exe";
    if (!fs::exists(script_path)) {
        Logger::log(Logger::WARNING, "Auto-sync: script missing at " + script_path.string() + "; skipping");
        return;
    }

    std::wstring quoted_script = L"\"" + script_path.wstring() + L"\"";
    std::wstring args = quoted_script + L" --mode testing --register-with-server";
    std::wstring working_dir = exe_dir.wstring();

    // Build a command that tries venv -> py -3 -> python, same order as run_sync_types_command.
    // We wrap in cmd /c so we can chain with || (fallback).
    std::wstring command;
    if (fs::exists(venv_python)) {
        command = L"cmd.exe /c \"\"" + venv_python.wstring() + L"\" " + args + L" || py -3 " + args + L" || python " + args + L"\"";
    } else {
        command = L"cmd.exe /c \"py -3 " + args + L" || python " + args + L"\"";
    }

    STARTUPINFOW si{};
    PROCESS_INFORMATION pi{};
    si.cb = sizeof(si);
    si.dwFlags = STARTF_USESHOWWINDOW;
    si.wShowWindow = SW_HIDE;

    std::wstring mutable_cmd = command;
    DWORD flags = CREATE_NO_WINDOW | DETACHED_PROCESS;
    BOOL ok = CreateProcessW(
        nullptr,
        mutable_cmd.data(),
        nullptr, nullptr, FALSE,
        flags,
        nullptr,
        working_dir.c_str(),
        &si, &pi
    );
    if (!ok) {
        Logger::log(Logger::WARNING, "Auto-sync: CreateProcessW failed (" + std::to_string(GetLastError()) + "); skipping");
        return;
    }
    // Don't wait. Don't block the map-change flow.
    CloseHandle(pi.hThread);
    CloseHandle(pi.hProcess);
    Logger::log(Logger::INFO, "Auto-sync: background testing sync started");
}

// New functions for file association and permission checks
bool verify_file_association() {
    HKEY hKey;
    LONG result = RegOpenKeyExA(HKEY_CLASSES_ROOT, ".map", 0, KEY_READ, &hKey);
    if (result != ERROR_SUCCESS) {
        // std::cerr << "Map file association not found. Please run with --setup first." << std::endl;
        return false;
    }
    RegCloseKey(hKey);
    return true;
}

bool verify_permissions(const std::string& path) {
    try {
        fs::path dirPath = fs::path(path);
        if (!fs::exists(dirPath)) {
            // std::cerr << "Path does not exist: " << path << std::endl;
            return false;
        }

        // Check if we can list directory contents
        std::error_code ec;
        fs::directory_iterator it(dirPath, ec);
        if (ec) {
            // std::cerr << "Cannot access directory: " << path << " - " << ec.message() << std::endl;
            return false;
        }

        // Try to create a temporary file to test write permissions
        fs::path testFile = dirPath / "permission_test.tmp";
        {
            std::ofstream test(testFile);
            if (!test) {
                // std::cerr << "Cannot write to directory: " << path << std::endl;
                return false;
            }
        }
        fs::remove(testFile);

        return true;
    }
    catch (const std::exception& e) {
        // std::cerr << "Permission check failed: " << e.what() << std::endl;
        return false;
    }
}

bool is_map_path_valid(const std::string& mapPath, std::string& error) {
    if (mapPath.empty()) {
        error = "Map path is empty";
        return false;
    }

    fs::path path(mapPath);
    if (!fs::exists(path)) {
        error = "Map file does not exist: " + mapPath;
        return false;
    }

    if (fs::is_directory(path)) {
        error = "Path is a directory, not a file: " + mapPath;
        return false;
    }

    std::string extension = path.extension().string();
    if (extension != ".map") {
        error = "File is not a map file (wrong extension): " + mapPath;
        return false;
    }

    return true;
}

bool is_backup_map(const std::string& path) {
    return path.find("_backup.map") != std::string::npos;
}

std::string get_original_map_name(const std::string& backup_path) {
    // Remove _backup.map from the end to get original name
    size_t pos = backup_path.find("_backup.map");
    if (pos != std::string::npos) {
        return backup_path.substr(0, pos) + ".map";
    }
    return backup_path;
}

bool restore_from_backup(SOCKET sock, const std::string& backup_path) {
    if (!fs::exists(backup_path)) {
        // std::cout << "Error: Backup file does not exist: " << backup_path << std::endl;
        return false;
    }

    std::string current_map = get_current_map(sock);
    if (current_map.empty()) {
        // std::cout << "Error: Could not determine current map" << std::endl;
        return false;
    }

    // Get the original map name from backup
    std::string original_map = get_original_map_name(backup_path);
    // std::cout << "Restoring from backup: " << backup_path << " to " << original_map << std::endl;

    // Copy backup to original location
    try {
        fs::copy_file(backup_path, original_map, fs::copy_options::overwrite_existing);
        // std::cout << "Successfully restored from backup" << std::endl;
    } catch (const std::exception& e) {
        // std::cout << "Error restoring from backup: " << e.what() << std::endl;
        return false;
    }

    // Send hot_reload command to preserve player positions
    std::string reload_cmd = "hot_reload";
    if (!send_command(sock, reload_cmd)) {
        // std::cout << "Error sending hot_reload command" << std::endl;
        return false;
    }

    // Wait for reload to complete
    Sleep(200); // Reduced from 1000ms to 200ms

    // Verify the server is responsive
    std::string verify_cmd = "status";
    if (!send_command(sock, verify_cmd)) {
        // std::cout << "Warning: Server not responsive after hot reload" << std::endl;
        return false;
    }

    // std::cout << "Map restore completed successfully" << std::endl;
    return true;
}

bool handle_map_replacement(SOCKET sock, const std::string& map_path, bool skip_backup = false) {
    try {
        Logger::log(Logger::INFO, "Starting map replacement process for: " + map_path);

        // Preflight: ensure directories
        std::string maps_dir_s = get_or_create_maps_directory();
        if (maps_dir_s.empty()) { Logger::log(Logger::ERROR, "Failed to resolve/create DDNet maps directory"); return false; }
        std::string backups_dir_s = get_or_create_backups_directory();
        if (backups_dir_s.empty()) { Logger::log(Logger::ERROR, "Failed to resolve/create backups directory"); return false; }
        fs::path maps_dir = fs::path(maps_dir_s);
        fs::path backups_dir = fs::path(backups_dir_s);

        // Decide reload method based on current server map
        std::string current_map = get_current_map(sock);
        if (current_map.empty()) { Logger::log(Logger::ERROR, "Could not determine current map"); return false; }
        bool need_change_to_tutorial = (current_map != "Tutorial");
        Logger::log(Logger::INFO, std::string("Current map: ") + current_map + (need_change_to_tutorial ? " (will change_map Tutorial)" : " (will hot_reload)"));

        // Paths
        fs::path original_path = fs::path(map_path);                           // LINEAR1
        fs::path ddnet_copy_path = maps_dir / original_path.filename();        // LINEAR2
        fs::path tutorial_path = maps_dir / "Tutorial.map";                   // LINEAR3 (working file)

        // If Tutorial.map missing, create blank and marker in backups
        if (!fs::exists(tutorial_path)) {
            try {
                std::ofstream blank(tutorial_path, std::ios::binary); blank.close();
                Logger::log(Logger::INFO, "Created blank Tutorial.map: " + tutorial_path.string());
                fs::path marker = next_marker_path(backups_dir, "Tutorial map not exist.map");
                std::ofstream mk(marker, std::ios::binary); mk.close();
                Logger::log(Logger::INFO, "Created marker: " + marker.string());
            } catch (const std::exception& e) {
                Logger::log(Logger::ERROR, std::string("Failed to create Tutorial or marker: ") + e.what());
                return false;
            }
        }

        // Backups to backups/ with timestamp and lastmapname hint (no generic Tutorial_<ts>.map)
        const std::string ts = make_timestamp();
        if (!skip_backup) {
            try {
                std::string last_new_map, last_current_map;
                read_lastmap(last_new_map, last_current_map);
                if (!last_new_map.empty()) {
                    fs::path named = backups_dir / (last_new_map + "_" + ts + ".map");
                    if (fs::exists(tutorial_path)) {
                        fs::copy_file(tutorial_path, named, fs::copy_options::overwrite_existing);
                        Logger::log(Logger::INFO, "Backup created: " + named.string());
                    }
                } else {
                    // No lastmapname.txt -> create explicit marker
                    fs::path no_txt = backups_dir / "lastmapname not exist.map";
                    std::ofstream f(no_txt, std::ios::binary); f.close();
                    Logger::log(Logger::INFO, "Created marker: " + no_txt.string());
                }
            } catch (const std::exception& e) {
                Logger::log(Logger::ERROR, std::string("Error creating backups: ") + e.what());
                return false;
            }
        }

        // LINEAR2: Copy original to DDNet maps directory if missing
        try {
            if (!fs::exists(ddnet_copy_path)) {
                fs::copy_file(original_path, ddnet_copy_path, fs::copy_options::none);
                Logger::log(Logger::INFO, "Created LINEAR2 copy in DDNet maps: " + ddnet_copy_path.string());
            }
        } catch (const std::exception& e) {
            Logger::log(Logger::ERROR, "Error creating LINEAR2 copy: " + std::string(e.what()));
            return false;
        }

        // Save Last Map Name before replacement: "new_map"(current_map)
        {
            const std::string new_map_name = original_path.stem().string();
            if (!write_lastmap(new_map_name, current_map)) {
                Logger::log(Logger::ERROR, "Failed to update lastmapname.txt");
            } else {
                Logger::log(Logger::INFO, std::string("Updated lastmapname.txt to \"") + new_map_name + "\"(" + current_map + ")");
            }
        }

        // LINEAR3: Overwrite Tutorial.map with new map
        // Skip copy if source and destination are the same file
        if (fs::equivalent(original_path, tutorial_path)) {
            Logger::log(Logger::INFO, "Source and destination are the same file, skipping copy: " + tutorial_path.string());
        } else {
            try {
                fs::copy_file(original_path, tutorial_path, fs::copy_options::overwrite_existing);
                Logger::log(Logger::INFO, "Updated Tutorial.map with new content: " + tutorial_path.string());
            } catch (const std::exception& e) {
                Logger::log(Logger::ERROR, "Error creating LINEAR3 copy: " + std::string(e.what()));
                return false;
            }
        }

        // Send change_map or hot_reload
        if (need_change_to_tutorial) {
            if (!change_map(sock, "Tutorial")) {
                Logger::log(Logger::ERROR, "Failed to send change_map Tutorial");
                return false;
            }
            Logger::log(Logger::INFO, "Sent change_map Tutorial");
        } else {
            if (!send_command(sock, "hot_reload")) {
                Logger::log(Logger::ERROR, "Error sending hot_reload command");
                return false;
            }
            Logger::log(Logger::INFO, "Hot reload command sent successfully");
        }

        // Wait for reload to complete
        Sleep(200);

        // Verify the server is responsive
        std::string verify_cmd = "status";
        if (!send_command(sock, verify_cmd)) {
            Logger::log(Logger::WARNING, "Server not responsive after hot reload");
            return false;
        }
        Logger::log(Logger::INFO, "Map replacement completed successfully");

        // TRIG-04: auto-trigger testing-only sync after RCON map change (debounced)
        trigger_background_testing_sync_if_due();

        return true;
    }
    catch (const std::exception& e) {
        Logger::log(Logger::ERROR, "Error in handle_map_replacement: " + std::string(e.what()));
        return false;
    }
}

// Enhanced map validation
bool validate_map_file(const fs::path& mapPath) {
    Logger::log(Logger::DEBUG, "Validating map file: " + mapPath.string());
    
    std::ifstream file(mapPath, std::ios::binary);
    if (!file) {
        Logger::log(Logger::ERROR, "Could not open map file: " + mapPath.string());
        return false;
    }
    
    try {
        MapFileHeader header;
        file.read(reinterpret_cast<char*>(&header), sizeof(header));
        
        // Check magic number
        std::string magic(header.magic, 4);
        if (magic != "DATA" && magic != "ATAD") {
            Logger::log(Logger::ERROR, "Invalid map file magic number: " + magic);
            return false;
        }
        
        // Check version
        if (header.version < 1 || header.version > 5) {
            Logger::log(Logger::ERROR, "Unsupported map version: " + std::to_string(header.version));
            return false;
        }
        
        // Check size
        if (header.size <= 0 || header.size > 1024*1024*64) { // Max 64MB
            Logger::log(Logger::ERROR, "Invalid map size: " + std::to_string(header.size));
            return false;
        }
        
        Logger::log(Logger::INFO, "Map validation successful");
        return true;
    } catch (const std::exception& e) {
        Logger::log(Logger::ERROR, "Error validating map file: " + std::string(e.what()));
        return false;
    }
}

// Windows GUI entry point - no console window
int WINAPI WinMain(HINSTANCE hInstance, HINSTANCE hPrevInstance, LPSTR lpCmdLine, int nCmdShow) {
    // Convert command line to argc/argv
    int argc;
    LPWSTR* argvW = CommandLineToArgvW(GetCommandLineW(), &argc);
    
    // Convert wide strings to narrow strings
    std::vector<std::string> argStrings;
    std::vector<char*> argv;
    for (int i = 0; i < argc; i++) {
        int size = WideCharToMultiByte(CP_UTF8, 0, argvW[i], -1, nullptr, 0, nullptr, nullptr);
        std::string str(size - 1, 0);
        WideCharToMultiByte(CP_UTF8, 0, argvW[i], -1, &str[0], size, nullptr, nullptr);
        argStrings.push_back(str);
    }
    LocalFree(argvW);
    
    for (auto& s : argStrings) {
        argv.push_back(&s[0]);
    }
    argv.push_back(nullptr);
    
    Logger::log(Logger::INFO, "Starting DDNet Map Control (silent mode)");

    if (is_sync_types_command(argc, argv.data())) {
        return run_sync_types_command(argc, argv.data());
    }

    // Ensure Winsock is initialized before any socket use
    WsaSession wsa;
    if (!wsa.ok) {
        Logger::log(Logger::ERROR, "Failed to initialize Winsock (WSAStartup)");
        return 1;
    }

    // Handle setup command
    if (is_setup_command(argc, argv.data())) {
        Logger::log(Logger::INFO, "Setting up file associations");
        if (setupFileAssociation()) {
            Logger::log(Logger::INFO, "File associations setup successfully");
            return 0;
        }
        Logger::log(Logger::ERROR, "Failed to setup file associations");
        return 1;
    }

    // Handle restore command
    if (is_restore_command(argc, argv.data())) {
        Logger::log(Logger::INFO, "Starting restore process");
        SOCKET sock = create_and_connect_socket();
        if (sock == INVALID_SOCKET) {
            Logger::log(Logger::ERROR, "Failed to connect to server");
            return 1;
        }
        
        if (restore_backup(sock)) {
            Logger::log(Logger::INFO, "Restore completed successfully");
            closesocket(sock);
            return 0;
        }
        Logger::log(Logger::ERROR, "Failed to restore backup");
        closesocket(sock);
        return 1;
    }

    // Regular map replacement process
    if (argc != 2) {
        Logger::log(Logger::ERROR, "Invalid number of arguments");
        print_usage(argv.data()[0]);
        return 1;
    }

    std::string map_path = argv.data()[1];
    Logger::log(Logger::INFO, "Processing map: " + map_path);

    // Validate map file
    if (!validate_map_file(fs::path(map_path))) {
        Logger::log(Logger::ERROR, "Map validation failed");
        return 1;
    }

    // Check if server is running
    if (!is_server_running()) {
        Logger::log(Logger::ERROR, "DDNet server is not running");
        return 1;
    }

    // Connect to server
    SOCKET sock = create_and_connect_socket();
    if (sock == INVALID_SOCKET) {
        Logger::log(Logger::ERROR, "Failed to connect to server");
        return 1;
    }

    // Set socket timeout
    if (!set_socket_timeout(sock, ServerConfig::DEFAULT_TIMEOUT_MS)) {
        Logger::log(Logger::ERROR, "Failed to set socket timeout");
        closesocket(sock);
        return 1;
    }

    // Authenticate
    if (!authenticate(sock)) {
        Logger::log(Logger::ERROR, "Authentication failed");
        closesocket(sock);
        return 1;
    }

    // Clean up old backups
    cleanup_old_backups(fs::path(get_maps_directory()));

    // Handle map replacement
    bool success = handle_map_replacement(sock, map_path);
    closesocket(sock);

    if (success) {
        Logger::log(Logger::INFO, "Map replacement completed successfully");
        return 0;
    } else {
        Logger::log(Logger::ERROR, "Map replacement failed");
        return 1;
    }
}

void print_usage(const char* program_name) {
    // std::cout << "Usage: " << program_name << " <path_to_map_file> [--restore] [--setup]" << std::endl;
    // std::cout << "Options:" << std::endl;
    // std::cout << "  --restore    Restore the last backup instead of replacing the map" << std::endl;
    // std::cout << "  --setup      Set up .map file associations (requires admin privileges)" << std::endl;
}

std::vector<std::string> get_responses(SOCKET sock, int maxResponses, int timeoutMs) {
    std::vector<std::string> responses;
    char buffer[4096];
    
    // std::cout << "Waiting for responses (timeout: " << timeoutMs << "ms)..." << std::endl;
    
    // Set socket timeout
    DWORD timeout = timeoutMs;
    setsockopt(sock, SOL_SOCKET, SO_RCVTIMEO, (char*)&timeout, sizeof(timeout));
    
    while (responses.size() < maxResponses) {
        int bytesReceived = recv(sock, buffer, sizeof(buffer) - 1, 0);
        if (bytesReceived <= 0) break; // Exit immediately on any error or timeout
        
        buffer[bytesReceived] = '\0';
        responses.push_back(std::string(buffer));
        
        // Quick parse for output if needed
        std::istringstream iss(buffer);
        std::string line;
        while (std::getline(iss, line)) {
            if (!line.empty()) {
                // std::cout << "Received: " << line << std::endl;
            }
        }
    }
    
    return responses;
}
