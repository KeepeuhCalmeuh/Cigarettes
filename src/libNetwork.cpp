#include "libNetwork.hpp"
#include <iostream>
#include <stdexcept>
#include <cstring>
#include <chrono>
#include <openssl/rand.h>

#ifndef _WIN32
    #include <sys/socket.h>
    #include <arpa/inet.h>
    #include <unistd.h>
    #include <fcntl.h>
    #define closesocket close
#else
    #pragma comment(lib, "ws2_32.lib")
#endif

void Network::init_sockets() {
#ifdef _WIN32
    WSADATA wsaData;
    if (WSAStartup(MAKEWORD(2, 2), &wsaData) != 0) {
        throw std::runtime_error("WSAStartup failed");
    }
#endif
}

void Network::cleanup_sockets() {
#ifdef _WIN32
    WSACleanup();
#endif
}

Network::Network(int service_port, const std::string& install_dir, int socks_port, const std::string& version) 
    : tor_service_port(service_port), tor_socks_port(socks_port), server_socket(INVALID_SOCKET_VAL), client_socket(INVALID_SOCKET_VAL), connected(false), is_running(false) 
{
    init_sockets();
    tor_manager = std::make_unique<TorManager>(service_port, install_dir, socks_port, version);
    if (!tor_manager->start()) {
        throw std::runtime_error("Failed to start Tor");
    }

    is_running = true;
    
    // We can start the listener thread immediately, but io_thread needs connected to be true to do meaningful work.
    listener_thread = std::thread(&Network::listener_loop, this);
    io_thread = std::thread(&Network::io_loop, this);
}

Network::~Network() {
    is_running = false;
    disconnect();
    
    if (server_socket != INVALID_SOCKET_VAL) {
        closesocket(server_socket);
        server_socket = INVALID_SOCKET_VAL;
    }

    if (listener_thread.joinable()) listener_thread.join();
    if (io_thread.joinable()) io_thread.join();

    if (tor_manager) {
        tor_manager->stop();
    }
    cleanup_sockets();
}

bool Network::socks5_connect(const std::string& onion_host, int port) {
    std::cout << "[SOCKS5] Connecting to Tor proxy at 127.0.0.1:" << tor_socks_port << "...\n";
    client_socket = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    if (client_socket == INVALID_SOCKET_VAL) return false;

    sockaddr_in socks_addr;
    socks_addr.sin_family = AF_INET;
    socks_addr.sin_port = htons(tor_socks_port);
    inet_pton(AF_INET, "127.0.0.1", &socks_addr.sin_addr);

    if (::connect(client_socket, (struct sockaddr*)&socks_addr, sizeof(socks_addr)) < 0) {
        std::cerr << "[SOCKS5] Error connecting to local Tor proxy!\n";
        return false;
    }

    std::cout << "[SOCKS5] Sending Auth request...\n";
    // Step 1: Auth request
    uint8_t auth_req[3] = {0x05, 0x01, 0x00};
    send(client_socket, (char*)auth_req, 3, 0);

    uint8_t auth_resp[2];
    if (recv(client_socket, (char*)auth_resp, 2, 0) != 2) {
        std::cerr << "[SOCKS5] Auth response recv failed\n";
        return false;
    }
    if (auth_resp[0] != 0x05 || auth_resp[1] != 0x00) {
        std::cerr << "[SOCKS5] Auth rejected by Tor\n";
        return false;
    }

    std::cout << "[SOCKS5] Auth OK, requesting target onion " << onion_host << ":" << port << "...\n";
    // Step 2: Connect request
    std::vector<uint8_t> conn_req;
    conn_req.push_back(0x05); // Version
    conn_req.push_back(0x01); // Connect command
    conn_req.push_back(0x00); // Reserved
    conn_req.push_back(0x03); // Domain name address type
    conn_req.push_back(static_cast<uint8_t>(onion_host.length()));
    
    for (char c : onion_host) conn_req.push_back(c);
    
    conn_req.push_back((port >> 8) & 0xFF);
    conn_req.push_back(port & 0xFF);

    send(client_socket, (char*)conn_req.data(), conn_req.size(), 0);

    // Read response
    uint8_t resp_header[4];
    if (recv(client_socket, (char*)resp_header, 4, 0) != 4) {
        std::cerr << "[SOCKS5] Did not receive 4 byte header from Tor\n";
        return false;
    }
    
    if (resp_header[0] != 0x05 || resp_header[1] != 0x00) {
        std::cerr << "[SOCKS5] Connection to onion failed. Status byte: " << (int)resp_header[1] << "\n";
        return false;
    }

    if (resp_header[3] == 0x01) { // IPv4
        uint8_t dummy[6];
        recv(client_socket, (char*)dummy, 6, 0);
    } else if (resp_header[3] == 0x03) { // Domain
        uint8_t len;
        recv(client_socket, (char*)&len, 1, 0);
        std::vector<uint8_t> dummy(len + 2); // len + 2 bytes for port
        recv(client_socket, (char*)dummy.data(), dummy.size(), 0);
    } else if (resp_header[3] == 0x04) { // IPv6
        uint8_t dummy[18];
        recv(client_socket, (char*)dummy, 18, 0);
    } else {
        std::cerr << "[SOCKS5] Invalid address format in response\n";
        return false;
    }

    std::cout << "[SOCKS5] Connection to peer successful!\n";
    return true;
}

void Network::connect(const std::string& own_onion_address, const std::vector<uint8_t>& own_fingerprint, 
                      const std::string& peer_onion_address, const std::vector<uint8_t>& peer_fingerprint) {
    if (connected) return;

    if (!socks5_connect(peer_onion_address, 80)) {
        std::cerr << "Failed to connect via SOCKS5 proxy to " << peer_onion_address << "\n";
        return; // Don't throw to not crash CLI, just don't connect
    }

    this->peer_onion_address = peer_onion_address;
    this->peer_fingerprint = peer_fingerprint;
    connected = true;
}

void Network::disconnect() {
    // Appelé uniquement par io_loop (perte de connexion) et le destructeur
    // Ne pas envoyer 0x05 ici : ProtocolHandler s'en charge avant d'appeler close_connection()
    close_connection();
}

void Network::close_connection() {
    connected = false;
    peer_onion_address.clear();
    peer_fingerprint.clear();
    
    {
        std::lock_guard<std::mutex> lock(socket_mutex);
        if (client_socket != INVALID_SOCKET_VAL) {
            closesocket(client_socket);
            client_socket = INVALID_SOCKET_VAL;
        }
    }
    
    std::lock_guard<std::mutex> lock(outgoing_mutex);
    while (!outgoing_messages.empty()) outgoing_messages.pop();
}

bool Network::flush_outgoing(int timeout_ms) {
    auto start = std::chrono::steady_clock::now();
    while (true) {
        {
            std::lock_guard<std::mutex> lock(outgoing_mutex);
            if (outgoing_messages.empty()) return true;
        }
        
        auto now = std::chrono::steady_clock::now();
        if (std::chrono::duration_cast<std::chrono::milliseconds>(now - start).count() > timeout_ms) {
            return false;
        }
        std::this_thread::sleep_for(std::chrono::milliseconds(10));
    }
}

bool Network::isConnected() const {
    return connected;
}


void Network::sendMessage(const std::vector<uint8_t>& payload, uint16_t message_type) {
    std::vector<uint8_t> msg = format_message(payload, message_type);
    std::lock_guard<std::mutex> lock(outgoing_mutex);
    if (outgoing_messages.size() >= MAX_QUEUE_SIZE) {
        std::cerr << "[Network] Outgoing queue full, dropping message type 0x" 
                  << std::hex << message_type << std::dec << "\n";
        return;
    }
    outgoing_messages.push(msg);
}

bool Network::receiveMessage(std::vector<uint8_t>& out_payload, uint16_t& out_message_type) {
    std::lock_guard<std::mutex> lock(incoming_mutex);
    if (incoming_messages.empty()) return false;
    
    out_payload = incoming_messages.front();
    incoming_messages.pop();
    out_message_type = 0;
    return true;
}

std::string Network::get_onion() const {
    if (tor_manager) {
        return tor_manager->getOnionAddress();
    }
    return "";
}

std::vector<uint8_t> Network::format_message(const std::vector<uint8_t>& payload, uint16_t message_type) {
    std::vector<uint8_t> body;
    
    // 8 bytes: message type
    for (int i = 0; i < 8; ++i) {
        if (i == 0) body.push_back(message_type & 0xFF);
        else if (i == 1) body.push_back((message_type >> 8) & 0xFF);
        else body.push_back(0);
    }

    // N bytes: payload
    body.insert(body.end(), payload.begin(), payload.end());
    
    // 8 bytes: timestamp
    uint64_t timestamp = std::chrono::duration_cast<std::chrono::milliseconds>(
        std::chrono::system_clock::now().time_since_epoch()).count();
    for (int i = 0; i < 8; ++i) {
        body.push_back((timestamp >> (i * 8)) & 0xFF);
    }

    // Calculate padding to make total TCP frame length a multiple of 512 bytes.
    // Total frame = 4 (length header) + body.size() + P (padding) + 2 (padding length)
    size_t current_len = 4 + body.size() + 2;
    size_t remainder = current_len % 512;
    size_t padding_len = (512 - remainder) % 512;

    std::vector<uint8_t> padding(padding_len);
    if (padding_len > 0) {
        RAND_bytes(padding.data(), padding_len);
    }

    body.insert(body.end(), padding.begin(), padding.end());
    body.push_back((padding_len >> 0) & 0xFF);
    body.push_back((padding_len >> 8) & 0xFF);

    // Prepend 4-byte length
    uint32_t total_len = (uint32_t)body.size();
    std::vector<uint8_t> message;
    message.push_back((total_len >> 0) & 0xFF);
    message.push_back((total_len >> 8) & 0xFF);
    message.push_back((total_len >> 16) & 0xFF);
    message.push_back((total_len >> 24) & 0xFF);
    message.insert(message.end(), body.begin(), body.end());

    return message;
}

void Network::listener_loop() {
    server_socket = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    if (server_socket == INVALID_SOCKET_VAL) return;

    sockaddr_in server_addr;
    server_addr.sin_family = AF_INET;
    server_addr.sin_port = htons(tor_service_port);
    inet_pton(AF_INET, "127.0.0.1", &server_addr.sin_addr);

    // Reuse addr
    int opt = 1;
    setsockopt(server_socket, SOL_SOCKET, SO_REUSEADDR, (const char*)&opt, sizeof(opt));

    if (bind(server_socket, (struct sockaddr*)&server_addr, sizeof(server_addr)) < 0) {
        closesocket(server_socket);
        server_socket = INVALID_SOCKET_VAL;
        return;
    }

    if (listen(server_socket, 5) < 0) {
        closesocket(server_socket);
        server_socket = INVALID_SOCKET_VAL;
        return;
    }

    while (is_running) {
        fd_set readfds;
        FD_ZERO(&readfds);
        FD_SET(server_socket, &readfds);

        struct timeval tv;
        tv.tv_sec = 0;
        tv.tv_usec = 100000; // 100ms

        int ret = select(server_socket + 1, &readfds, NULL, NULL, &tv);
        if (ret > 0 && FD_ISSET(server_socket, &readfds)) {
            sockaddr_in client_addr;
            socklen_t client_len = sizeof(client_addr);
            socket_t incoming = accept(server_socket, (struct sockaddr*)&client_addr, &client_len);
            
            if (incoming != INVALID_SOCKET_VAL) {
                if (connected) {
                    std::cout << "[Network] Incoming connection rejected, already connected.\n";
                    // Already connected to a peer, refuse new connection to keep it simple
                    closesocket(incoming);
                } else {
                    std::cout << "[Network] Incoming Tor connection accepted!\n";
                    client_socket = incoming;
                    connected = true;
                }
            }
        }
    }
}

void Network::io_loop() {
    std::vector<uint8_t> recv_buffer;

    while (is_running) {
        socket_t sock;
        {
            std::lock_guard<std::mutex> lock(socket_mutex);
            sock = client_socket; // copie locale sûre
        }

        if (!connected || sock == INVALID_SOCKET_VAL) {
            recv_buffer.clear();
            std::this_thread::sleep_for(std::chrono::milliseconds(100));
            continue;
        }

        // Send
        {
            std::lock_guard<std::mutex> lock(outgoing_mutex);
            while (!outgoing_messages.empty()) {
                const auto& msg = outgoing_messages.front();
                size_t total_sent = 0;
                while (total_sent < msg.size()) {
                    int sent = send(sock, (char*)msg.data() + total_sent, msg.size() - total_sent, 0);
                    if (sent <= 0) break;
                    total_sent += sent;
                }
                outgoing_messages.pop();
            }
        }

        // Receive
        fd_set readfds;
        FD_ZERO(&readfds);
        FD_SET(sock, &readfds); // ← utilise la copie locale, pas client_socket directement

        struct timeval tv { 0, 10000 };
        int ret = select(sock + 1, &readfds, NULL, NULL, &tv);

        if (ret > 0 && FD_ISSET(sock, &readfds)) {
            char buffer[4096];
            int bytes_received = recv(sock, buffer, sizeof(buffer), 0);
            if (bytes_received > 0) {
                recv_buffer.insert(recv_buffer.end(), buffer, buffer + bytes_received);
            } else {
                disconnect();
                recv_buffer.clear();
                continue;
            }
        }

        // Parse complete messages from recv_buffer
        // Message format: [4 bytes total_body_len][8 bytes type][payload][8 bytes timestamp]
        while (recv_buffer.size() >= 4) {
            uint32_t body_len = (uint32_t)recv_buffer[0]
                              | ((uint32_t)recv_buffer[1] << 8)
                              | ((uint32_t)recv_buffer[2] << 16)
                              | ((uint32_t)recv_buffer[3] << 24);

            if (body_len > MAX_MESSAGE_SIZE) { // Sanity check
                std::cerr << "[Network] Oversized/corrupt message frame (" << body_len << " bytes), dropping connection\n";
                disconnect();
                recv_buffer.clear();
                break;
            }

            if (recv_buffer.size() < 4 + body_len) {
                break; // Wait for more data
            }

            // We have a full message body
            std::vector<uint8_t> full_msg(recv_buffer.begin() + 4, recv_buffer.begin() + 4 + body_len);
            recv_buffer.erase(recv_buffer.begin(), recv_buffer.begin() + 4 + body_len);

            // Strip padding if present (last 2 bytes represent padding length)
            if (full_msg.size() >= 2) {
                uint16_t padding_len = full_msg[full_msg.size() - 2] | (full_msg[full_msg.size() - 1] << 8);
                if (full_msg.size() >= 2 + (size_t)padding_len) {
                    full_msg.resize(full_msg.size() - 2 - padding_len);
                } else {
                    std::cerr << "[Network] Corrupt padding length, dropping connection\n";
                    disconnect();
                    recv_buffer.clear();
                    break;
                }
            }

            {
                std::lock_guard<std::mutex> lock(incoming_mutex);
                if (incoming_messages.size() >= MAX_QUEUE_SIZE) {
                    std::cerr << "[Network] Incoming queue full, dropping connection\n";
                    disconnect();
                    recv_buffer.clear();
                    break;
                }
                incoming_messages.push(full_msg);
            }
        }
    }
}