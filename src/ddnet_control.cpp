#include <iostream>
#include <string>
#include <fstream>
#include <filesystem>
#include <WS2tcpip.h>
#include <chrono>
#include <thread>
#include <vector>
#include <conio.h>  // for _getch()
#include <windows.h>  // for SetConsoleTitle
#include <sstream>
#include <algorithm> // Added for std::remove_if
#include <shlobj.h> // Added for SHGetKnownFolderPath
#pragma comment(lib, "ws2_32.lib")
#pragma comment(lib, "shell32.lib")
#pragma comment(lib, "advapi32.lib")  // Added for registry functions

namespace fs = std::filesystem;

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
        std::cout << "Failed to set send timeout: " << WSAGetLastError() << std::endl;
        return false;
    }
    
    // Set receive timeout
    if (setsockopt(sock, SOL_SOCKET, SO_RCVTIMEO, (char*)&timeout, sizeof(timeout)) != 0) {
        std::cout << "Failed to set receive timeout: " << WSAGetLastError() << std::endl;
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
        std::cerr << "Failed to send command: " << WSAGetLastError() << std::endl;
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
            std::cerr << "Error receiving data: " << error << std::endl;
            return false;
        }
        if (bytes_received == 0) {
            std::cerr << "Connection closed by server" << std::endl;
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

bool authenticate(SOCKET sock) {
    // Send password immediately without waiting
    send_command(sock, "test123\n");

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
    std::cout << "\n=== Starting Map Query ===" << std::endl;
    std::cout << "Sending sv_map command..." << std::endl;
    
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

    std::cout << "Response: " << response << std::endl;
    std::cout << "\n";

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
            
            std::cerr << "Connection attempt " << attempt << " failed. ";
            if (attempt < retries) {
                std::cerr << "Retrying in " << ServerConfig::RETRY_DELAY_MS << "ms..." << std::endl;
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
            
            std::cerr << "Send attempt " << attempt << " failed. ";
            if (attempt < retries) {
                std::cerr << "Retrying..." << std::endl;
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
            
            std::cerr << "Receive attempt " << attempt << " failed. ";
            if (attempt < retries) {
                std::cerr << "Retrying..." << std::endl;
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
        std::cerr << "Failed to establish server connection" << std::endl;
        return false;
    }

    if (!conn.send_command_with_retry("hot_reload")) {
        std::cerr << "Failed to send hot_reload command" << std::endl;
        return false;
    }

    std::vector<std::string> responses;
    if (!conn.receive_with_retry(responses)) {
        std::cerr << "Failed to receive response for hot_reload" << std::endl;
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
            std::cerr << "Attempt " << attempt << ": Failed to get current map" << std::endl;
        } else {
            // For hot reload, we just need to verify the server is responsive
            std::cout << "Hot reload verification successful!" << std::endl;
            return true;
        }

        if (attempt < MAX_RETRIES) {
            std::cout << "Retry " << attempt + 1 << "/" << MAX_RETRIES << std::endl;
            std::this_thread::sleep_for(std::chrono::milliseconds(RETRY_DELAY_MS));
        }
    }

    std::cerr << "Failed to verify server response after " << MAX_RETRIES << " attempts" << std::endl;
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
        return "";
    }

    return mapsPath.string();
}

bool setupFileAssociation() {
    HKEY hkey;
    const wchar_t* fileType = L".map";
    const wchar_t* appPath = L"\"C:\\Users\\rust-\\CascadeProjects\\ddnet_control\\ddnet_control_new.exe\" \"%1\"";
    
    // Create .map file association
    if (RegCreateKeyExW(HKEY_CLASSES_ROOT, fileType, 0, NULL, REG_OPTION_NON_VOLATILE,
        KEY_WRITE, NULL, &hkey, NULL) != ERROR_SUCCESS) {
        return false;
    }
    RegSetValueExW(hkey, NULL, 0, REG_SZ, (BYTE*)L"DDNetMapFile", 22);
    RegCloseKey(hkey);

    // Create command for .map files
    if (RegCreateKeyExW(HKEY_CLASSES_ROOT, L"DDNetMapFile\\shell\\open\\command", 
        0, NULL, REG_OPTION_NON_VOLATILE, KEY_WRITE, NULL, &hkey, NULL) != ERROR_SUCCESS) {
        return false;
    }
    RegSetValueExW(hkey, NULL, 0, REG_SZ, (BYTE*)appPath, (wcslen(appPath) + 1) * sizeof(wchar_t));
    RegCloseKey(hkey);

    return true;
}

bool file_exists(const std::string& path) {
    return fs::exists(path);
}

std::string get_map_name(const std::string& path) {
    return fs::path(path).stem().string();
}

// Map file validation structure
struct MapFileHeader {
    char magic[4];  // Should be "DATA" or "ATAD"
    int version;    // Map version
    int size;       // Map size
    int swaplen;    // Swap length
    int num_items;  // Number of items
    int num_raw;    // Number of raw items
};

bool validate_map_file(const std::string& mapPath) {
    std::ifstream file(mapPath, std::ios::binary);
    if (!file) {
        std::cerr << "Cannot open map file: " << mapPath << std::endl;
        return false;
    }

    MapFileHeader header;
    file.read(reinterpret_cast<char*>(&header), sizeof(header));

    if (!file) {
        std::cerr << "Failed to read map header: " << mapPath << std::endl;
        return false;
    }

    // Check magic number
    std::string magic(header.magic, 4);
    if (magic != "DATA" && magic != "ATAD") {
        std::cerr << "Invalid map file format: " << mapPath << std::endl;
        return false;
    }

    // Basic sanity checks
    if (header.size <= 0 || header.size > 1024*1024*64) {  // Max 64MB
        std::cerr << "Invalid map size: " << header.size << " bytes" << std::endl;
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
            std::cerr << "Failed to lock file: " << filePath << std::endl;
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
            std::cerr << "Map validation failed" << std::endl;
            return false;
        }

        std::string mapsDir = get_maps_directory();
        if (mapsDir.empty()) {
            return false;
        }

        // Get current map name from server
        std::string currentMap = get_current_map(sock);
        if (currentMap.empty()) {
            std::cerr << "Could not determine current map name" << std::endl;
            return false;
        }

        // Get map name without path
        std::string mapName = fs::path(mapPath).filename().string();
        fs::path targetPath = fs::path(mapsDir) / currentMap;
        std::string targetPathStr = targetPath.string() + ".map";

        // Create file lock
        FileLock lock(targetPathStr);
        if (!lock.acquire()) {
            std::cerr << "Map file is currently in use" << std::endl;
            return false;
        }

        // Get target file size
        std::error_code ec;
        uintmax_t targetSize = fs::file_size(mapPath, ec);
        if (ec) {
            std::cerr << "Failed to get source file size: " << ec.message() << std::endl;
            return false;
        }

        std::cout << "\n=== Copying Map to Server ===" << std::endl;
        std::cout << "Source map: " << mapPath << " (" << mapName << ")" << std::endl;
        std::cout << "Target map: " << targetPathStr << " (" << currentMap << ")" << std::endl;

        // Check if source map exists
        if (!fs::exists(mapPath)) {
            std::cerr << "Source map does not exist: " << mapPath << std::endl;
            return false;
        }

        // Try to copy with retries
        for (int attempt = 1; attempt <= 3; attempt++) {
            try {
                // If target exists, try to remove it first
                if (fs::exists(targetPath)) {
                    std::cout << "Removing existing map..." << std::endl;
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

                std::cout << "Successfully copied map file" << std::endl;
                return true;
            }
            catch (const fs::filesystem_error& e) {
                std::cout << "Copy attempt " << attempt << " failed: " << e.what() << std::endl;
                if (attempt < 3) {
                    std::cout << "Waiting before retry..." << std::endl;
                    std::this_thread::sleep_for(std::chrono::milliseconds(100)); // Reduced from 1000ms to 100ms
                }
            }
        }
        std::cerr << "Failed to copy map after 3 attempts" << std::endl;
        return false;
    }
    catch (const std::exception& e) {
        std::cerr << "Error copying map: " << e.what() << std::endl;
        return false;
    }
}

bool replace_map(MapInfo& mapInfo, SOCKET sock) {
    try {
        // Get current map name from server
        std::string serverMap = get_current_map(sock);
        if (serverMap.empty()) {
            std::cerr << "Could not determine current map name" << std::endl;
            return false;
        }

        std::string mapsDir = get_maps_directory();
        if (mapsDir.empty()) {
            std::cerr << "Could not find DDNet maps directory" << std::endl;
            return false;
        }

        // Set up paths
        fs::path backupPath = fs::path(mapsDir) / (serverMap + "_backup.map");
        fs::path currentMapPath = fs::path(mapsDir) / (serverMap + ".map");

        std::cout << "\n=== Map Replacement Process ===" << std::endl;
        std::cout << "Current server map: " << serverMap << std::endl;

        // Handle backup based on existence
        if (fs::exists(backupPath)) {
            std::cout << "Found existing backup at: " << backupPath.string() << std::endl;
            mapInfo.backupPath = backupPath.string();
            mapInfo.originalMap = serverMap;
        } else {
            // Create original backup since it doesn't exist
            try {
                fs::copy_file(currentMapPath, backupPath, fs::copy_options::none);
                std::cout << "Created backup at: " << backupPath.string() << std::endl;
                mapInfo.backupPath = backupPath.string();
                mapInfo.originalMap = serverMap;
                save_backup_info(mapInfo);
            }
            catch (const fs::filesystem_error& e) {
                std::cerr << "Failed to create original backup: " << e.what() << std::endl;
                return false;
            }
        }

        // Copy new map to server's map location
        try {
            std::cout << "\nCopying from: " << mapInfo.ddnetPath << std::endl;
            std::cout << "Copying to: " << currentMapPath.string() << std::endl;
            fs::copy_file(mapInfo.ddnetPath, currentMapPath, fs::copy_options::overwrite_existing);
            std::cout << "Successfully copied map to: " << currentMapPath.string() << std::endl;
        }
        catch (const fs::filesystem_error& e) {
            std::cerr << "Failed to copy map: " << e.what() << std::endl;
            return false;
        }

        // Send hot reload command
        if (!send_command(sock, "hot_reload")) {
            std::cerr << "Failed to send reload command" << std::endl;
            return false;
        }

        // Verify the hot reload
        if (!verify_hot_reload(sock, get_map_name(mapInfo.ddnetPath))) {
            std::cerr << "Failed to verify hot reload" << std::endl;
            return false;
        }

        return true;
    }
    catch (const std::exception& e) {
        std::cerr << "Error in replace_map: " << e.what() << std::endl;
        return false;
    }
}

bool restore_backup(SOCKET sock) {
    try {
        std::string serverMap = get_current_map(sock);
        if (serverMap.empty()) {
            std::cerr << "Could not determine current map name" << std::endl;
            return false;
        }

        std::string mapsDir = get_maps_directory();
        if (mapsDir.empty()) {
            std::cerr << "Could not find DDNet maps directory" << std::endl;
            return false;
        }

        // Setup paths - use server's current map name
        fs::path currentMapPath = fs::path(mapsDir) / (serverMap + ".map");
        fs::path backupPath = fs::path(mapsDir) / (serverMap + "_backup.map");

        std::cout << "\n=== Map Restore Process ===" << std::endl;
        std::cout << "Current server map: " << serverMap << std::endl;
        std::cout << "Original backup: " << backupPath.string() << std::endl;

        // Check if original backup exists
        if (!fs::exists(backupPath)) {
            std::cerr << "Original backup not found: " << backupPath.string() << std::endl;
            return false;
        }

        // Copy backup back to current map
        try {
            fs::copy_file(backupPath, currentMapPath, fs::copy_options::overwrite_existing);
            std::cout << "Successfully restored from original backup" << std::endl;
        }
        catch (const fs::filesystem_error& e) {
            std::cerr << "Failed to restore from backup: " << e.what() << std::endl;
            return false;
        }

        // Send reload command
        if (!send_command(sock, "hot_reload")) {
            std::cerr << "Failed to send reload command" << std::endl;
            return false;
        }

        // Verify the hot reload using the original map name
        if (!verify_hot_reload(sock, serverMap)) {
            std::cerr << "Failed to verify hot reload after restore" << std::endl;
            return false;
        }

        std::cout << "Map restore completed successfully" << std::endl;
        return true;
    }
    catch (const std::exception& e) {
        std::cerr << "Error in restore_backup: " << e.what() << std::endl;
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
    std::cout << "Connecting to DDNet server..." << std::endl;

    SOCKET sock = socket(AF_INET, SOCK_STREAM, 0);
    if (sock == INVALID_SOCKET) {
        std::cerr << "Failed to create socket: " << WSAGetLastError() << std::endl;
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
        std::cerr << "Failed to connect to server: ";
        switch (error) {
            case WSAECONNREFUSED:
                std::cerr << "Connection refused (Is the server running?)";
                break;
            case WSAETIMEDOUT:
                std::cerr << "Connection timed out";
                break;
            case WSAEHOSTUNREACH:
                std::cerr << "Host unreachable";
                break;
            default:
                std::cerr << "Error " << error;
        }
        std::cerr << std::endl;
        closesocket(sock);
        return INVALID_SOCKET;
    }

    std::cout << "Successfully connected to server" << std::endl;
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

// New functions for file association and permission checks
bool verify_file_association() {
    HKEY hKey;
    LONG result = RegOpenKeyExA(HKEY_CLASSES_ROOT, ".map", 0, KEY_READ, &hKey);
    if (result != ERROR_SUCCESS) {
        std::cerr << "Map file association not found. Please run with --setup first." << std::endl;
        return false;
    }
    RegCloseKey(hKey);
    return true;
}

bool verify_permissions(const std::string& path) {
    try {
        fs::path dirPath = fs::path(path);
        if (!fs::exists(dirPath)) {
            std::cerr << "Path does not exist: " << path << std::endl;
            return false;
        }

        // Check if we can list directory contents
        std::error_code ec;
        fs::directory_iterator it(dirPath, ec);
        if (ec) {
            std::cerr << "Cannot access directory: " << path << " - " << ec.message() << std::endl;
            return false;
        }

        // Try to create a temporary file to test write permissions
        fs::path testFile = dirPath / "permission_test.tmp";
        {
            std::ofstream test(testFile);
            if (!test) {
                std::cerr << "Cannot write to directory: " << path << std::endl;
                return false;
            }
        }
        fs::remove(testFile);

        return true;
    }
    catch (const std::exception& e) {
        std::cerr << "Permission check failed: " << e.what() << std::endl;
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
        std::cout << "Error: Backup file does not exist: " << backup_path << std::endl;
        return false;
    }

    std::string current_map = get_current_map(sock);
    if (current_map.empty()) {
        std::cout << "Error: Could not determine current map" << std::endl;
        return false;
    }

    // Get the original map name from backup
    std::string original_map = get_original_map_name(backup_path);
    std::cout << "Restoring from backup: " << backup_path << " to " << original_map << std::endl;

    // Copy backup to original location
    try {
        fs::copy_file(backup_path, original_map, fs::copy_options::overwrite_existing);
        std::cout << "Successfully restored from backup" << std::endl;
    } catch (const std::exception& e) {
        std::cout << "Error restoring from backup: " << e.what() << std::endl;
        return false;
    }

    // Send hot_reload command to preserve player positions
    std::string reload_cmd = "hot_reload";
    if (!send_command(sock, reload_cmd)) {
        std::cout << "Error sending hot_reload command" << std::endl;
        return false;
    }

    // Wait for reload to complete
    Sleep(200); // Reduced from 1000ms to 200ms

    // Verify the server is responsive
    std::string verify_cmd = "status";
    if (!send_command(sock, verify_cmd)) {
        std::cout << "Warning: Server not responsive after hot reload" << std::endl;
        return false;
    }

    std::cout << "Map restore completed successfully" << std::endl;
    return true;
}

bool handle_map_replacement(SOCKET sock, const std::string& map_path, bool skip_backup = false) {
    try {
        // Get current map name from server
        std::string current_map = get_current_map(sock);
        if (current_map.empty()) {
            std::cout << "Error: Could not determine current map" << std::endl;
            return false;
        }

        // Setup paths for LINEAR stages
        fs::path maps_dir = fs::path(get_maps_directory());
        fs::path original_path = fs::path(map_path);                      // LINEAR1: Original location
        fs::path ddnet_copy_path = maps_dir / original_path.filename();   // LINEAR2: DDNet maps copy
        fs::path current_map_path = maps_dir / (current_map + ".map");    // LINEAR3: Working copy
        fs::path backup_path = maps_dir / (current_map + "_backup.map");  // W_backup: Original backup

        std::cout << "\n=== Map Replacement Process ===" << std::endl;
        std::cout << "LINEAR1 (Original): " << original_path.string() << std::endl;
        std::cout << "LINEAR2 (DDNet): " << ddnet_copy_path.string() << std::endl;
        std::cout << "LINEAR3 (Working): " << current_map_path.string() << std::endl;

        // Create backup of current map (W_backup)
        if (!skip_backup) {
            if (fs::exists(backup_path)) {
                std::cout << "Found existing backup at: " << backup_path.string() << std::endl;
            } else {
                try {
                    fs::copy_file(current_map_path, backup_path, fs::copy_options::none);
                    std::cout << "Created backup at: " << backup_path.string() << std::endl;
                } catch (const std::exception& e) {
                    std::cout << "Error creating backup: " << e.what() << std::endl;
                    return false;
                }
            }
        }

        // LINEAR2: Copy to DDNet maps directory
        try {
            if (!fs::exists(ddnet_copy_path)) {
                fs::copy_file(original_path, ddnet_copy_path, fs::copy_options::none);
                std::cout << "Created LINEAR2 copy in DDNet maps: " << ddnet_copy_path.string() << std::endl;
            }
        } catch (const std::exception& e) {
            std::cout << "Error creating LINEAR2 copy: " << e.what() << std::endl;
            return false;
        }

        // LINEAR3: Create working copy
        try {
            fs::copy_file(original_path, current_map_path, fs::copy_options::overwrite_existing);
            std::cout << "Created LINEAR3 working copy at: " << current_map_path.string() << std::endl;
        } catch (const std::exception& e) {
            std::cout << "Error creating LINEAR3 copy: " << e.what() << std::endl;
            return false;
        }

        // Send hot_reload command to preserve player positions
        std::string reload_cmd = "hot_reload";
        if (!send_command(sock, reload_cmd)) {
            std::cout << "Error sending hot_reload command" << std::endl;
            return false;
        }

        // Wait for reload to complete
        Sleep(200);

        // Verify the server is responsive
        std::string verify_cmd = "status";
        if (!send_command(sock, verify_cmd)) {
            std::cout << "Warning: Server not responsive after hot reload" << std::endl;
            return false;
        }

        return true;
    }
    catch (const std::exception& e) {
        std::cout << "Error in handle_map_replacement: " << e.what() << std::endl;
        return false;
    }
}

int main(int argc, char* argv[]) {
    setupFileAssociation();

    if (argc != 2) {
        std::cout << "Usage: " << argv[0] << " <map_path or --restore>" << std::endl;
        return 1;
    }

    std::string arg = argv[1];
    
    // Initialize Winsock early as we need it for all operations
    WSADATA wsaData;
    if (WSAStartup(MAKEWORD(2, 2), &wsaData) != 0) {
        std::cerr << "Failed to initialize Winsock" << std::endl;
        return 1;
    }

    // Handle restore command or backup map file
    if (arg == "--restore" || is_backup_map(arg)) {
        SOCKET sock = create_and_connect_socket();
        if (sock == INVALID_SOCKET) {
            WSACleanup();
            return 1;
        }

        if (!authenticate(sock)) {
            closesocket(sock);
            WSACleanup();
            return 1;
        }

        bool success;
        if (arg == "--restore") {
            // Normal restore command
            success = restore_backup(sock);
        } else {
            // Clicked on a backup file
            std::string original_map = get_original_map_name(arg);
            std::cout << "Restoring from backup: " << arg << " to " << original_map << std::endl;
            success = restore_from_backup(sock, arg);
        }

        closesocket(sock);
        WSACleanup();
        return success ? 0 : 1;
    }
    
    // If the argument is a full path (from double-click), validate it
    std::string mapPath = arg;
    if (mapPath.find(".map") != std::string::npos) {
        if (!fs::exists(mapPath)) {
            std::cout << "Error: Map file does not exist: " << mapPath << std::endl;
            WSACleanup();
            return 1;
        }
        if (!validate_map_file(mapPath)) {
            std::cout << "Error: Invalid map file: " << mapPath << std::endl;
            WSACleanup();
            return 1;
        }
    }

    // Create socket and connect
    SOCKET sock = create_and_connect_socket();
    if (sock == INVALID_SOCKET) {
        WSACleanup();
        return 1;
    }

    if (!authenticate(sock)) {
        closesocket(sock);
        WSACleanup();
        return 1;
    }

    // Handle the map replacement, skip backup creation if we're handling a backup file
    bool success = handle_map_replacement(sock, mapPath, is_backup_map(mapPath));

    closesocket(sock);
    WSACleanup();
    return success ? 0 : 1;
}

void print_usage(const char* program_name) {
    std::cout << "Usage: " << program_name << " <path_to_map_file> [--restore] [--setup]" << std::endl;
    std::cout << "Options:" << std::endl;
    std::cout << "  --restore    Restore the last backup instead of replacing the map" << std::endl;
    std::cout << "  --setup      Set up .map file associations (requires admin privileges)" << std::endl;
}

std::vector<std::string> get_responses(SOCKET sock, int maxResponses, int timeoutMs) {
    std::vector<std::string> responses;
    char buffer[4096];
    
    std::cout << "Waiting for responses (timeout: " << timeoutMs << "ms)..." << std::endl;
    
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
                std::cout << "Received: " << line << std::endl;
            }
        }
    }
    
    return responses;
}
