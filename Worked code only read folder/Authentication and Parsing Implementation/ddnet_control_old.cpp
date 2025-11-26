#include <iostream>
#include <string>
#include <winsock2.h>
#include <vector>
#include <chrono>
#include <thread>
#include <sstream>
#pragma comment(lib, "ws2_32.lib")

// Forward declarations
std::vector<std::string> get_responses(SOCKET sock, int maxResponses, int timeoutMs);

// Function to send command to the server
void send_command(SOCKET sock, const std::string &command) {
    std::cout << "Sending command: " << command << std::endl;

    // Send the command
    int result = send(sock, command.c_str(), command.length(), 0);
    if (result == SOCKET_ERROR) {
        std::cerr << "Failed to send command. Error: " << WSAGetLastError() << std::endl;
    } else {
        std::cout << "Successfully sent " << result << " bytes" << std::endl;
    }
}

// Function to connect to the server
bool connect_to_server(SOCKET sock) {
    sockaddr_in serverAddr;
    serverAddr.sin_family = AF_INET;
    serverAddr.sin_port = htons(8303); // ECON port from myServerconfig.cfg
    serverAddr.sin_addr.s_addr = inet_addr("127.0.0.1"); // ECON bind address from myServerconfig.cfg

    std::cout << "Connecting to server: " << inet_ntoa(serverAddr.sin_addr) << ":" << ntohs(serverAddr.sin_port) << std::endl;

    if (connect(sock, (sockaddr*)&serverAddr, sizeof(serverAddr)) == SOCKET_ERROR) {
        std::cerr << "Failed to connect. Error: " << WSAGetLastError() << std::endl;
        return false;
    }

    std::cout << "Successfully connected to server" << std::endl;
    return true;
}

// Function to get responses from the server
std::vector<std::string> get_responses(SOCKET sock, int maxResponses, int timeoutMs) {
    std::vector<std::string> responses;
    char buffer[4096];
    int bytesReceived;
    
    std::cout << "Waiting for responses (timeout: " << timeoutMs << "ms)..." << std::endl;
    
    // Set socket timeout
    DWORD timeout = timeoutMs;
    if (setsockopt(sock, SOL_SOCKET, SO_RCVTIMEO, (char*)&timeout, sizeof(timeout)) == SOCKET_ERROR) {
        std::cerr << "Failed to set socket timeout. Error: " << WSAGetLastError() << std::endl;
        return responses;
    }
    
    while (responses.size() < maxResponses) {
        bytesReceived = recv(sock, buffer, sizeof(buffer) - 1, 0);
        if (bytesReceived == SOCKET_ERROR) {
            int error = WSAGetLastError();
            if (error == WSAETIMEDOUT) {
                std::cout << "No more responses (timeout)" << std::endl;
                break;
            }
            std::cerr << "Error receiving data: " << error << std::endl;
            break;
        }
        if (bytesReceived == 0) {
            std::cout << "Connection closed by server" << std::endl;
            break;
        }
        
        buffer[bytesReceived] = '\0';
        responses.push_back(std::string(buffer));
        
        // Print each line of the response
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

// Function to authenticate with the server
bool authenticate(SOCKET sock) {
    std::cout << "Starting authentication..." << std::endl;

    // Send just the password
    std::string auth_cmd = "test123\n";
    send_command(sock, auth_cmd);

    // Wait for response
    auto responses = get_responses(sock, 5, 2000);
    if (responses.empty()) {
        std::cerr << "No response from server during authentication" << std::endl;
        return false;
    }

    // Check for successful authentication
    for (const auto& response : responses) {
        std::cout << "Auth response: " << response << std::endl;
        if (response.find("Authentication successful") != std::string::npos) {
            std::cout << "Successfully authenticated!" << std::endl;
            return true;
        }
        if (response.find("Wrong password") != std::string::npos) {
            std::cerr << "Wrong password!" << std::endl;
            return false;
        }
    }

    std::cerr << "Authentication failed" << std::endl;
    return false;
}

std::string getCurrentMapName() {
    // Create TCP socket
    SOCKET sock = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    if (sock == INVALID_SOCKET) {
        std::cerr << "Failed to create socket. Error: " << WSAGetLastError() << std::endl;
        return "unknown";
    }

    // Set socket timeout
    DWORD timeout = 2000; // 2 seconds
    if (setsockopt(sock, SOL_SOCKET, SO_RCVTIMEO, (char*)&timeout, sizeof(timeout)) == SOCKET_ERROR) {
        std::cerr << "Failed to set socket timeout. Error: " << WSAGetLastError() << std::endl;
        closesocket(sock);
        return "unknown";
    }

    // Connect to server
    if (!connect_to_server(sock)) {
        closesocket(sock);
        return "unknown";
    }

    // Authenticate
    if (!authenticate(sock)) {
        closesocket(sock);
        return "unknown";
    }

    // Send sv_map command to get current map
    std::cout << "Sending sv_map command..." << std::endl;
    send_command(sock, "sv_map\n");

    // Get responses
    auto responses = get_responses(sock, 5, 2000);
    closesocket(sock);

    // Parse responses for map name
    for (const auto& response : responses) {
        std::cout << "Response: " << response << std::endl;
        // Look for "Value: " in the response
        size_t valuePos = response.find("Value: ");
        if (valuePos != std::string::npos) {
            // Extract everything after "Value: "
            std::string mapName = response.substr(valuePos + 7);
            // Remove any whitespace or newlines
            mapName.erase(0, mapName.find_first_not_of(" \n\r\t"));
            mapName.erase(mapName.find_last_not_of(" \n\r\t") + 1);
            if (!mapName.empty()) {
                return mapName;
            }
        }
    }

    return "unknown";
}

int main() {
    // Initialize Winsock
    std::cout << "Initializing Winsock..." << std::endl;
    WSADATA wsaData;
    if (WSAStartup(MAKEWORD(2, 2), &wsaData) != 0) {
        std::cerr << "Failed to initialize Winsock" << std::endl;
        return 1;
    }

    // Get the current map name
    std::string currentMap = getCurrentMapName();
    std::cout << "Current map: " << currentMap << std::endl;

    // Cleanup Winsock
    WSACleanup();
    return 0;
}
