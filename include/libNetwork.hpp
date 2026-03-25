#ifndef LIBNETWORK_HPP
#define LIBNETWORK_HPP

#include <vector>
#include <cstdint>
#include <string>
#include <memory>
#include <thread>
#include <mutex>
#include <queue>
#include <atomic>

#include "torManager.hpp"

#ifdef _WIN32
    #include <winsock2.h>
    #include <ws2tcpip.h>
    typedef SOCKET socket_t;
    #define INVALID_SOCKET_VAL INVALID_SOCKET
#else
    typedef int socket_t;
    #define INVALID_SOCKET_VAL -1
#endif

class Network {
public:
    Network(int service_port = 8080, 
            const std::string& install_dir = "tor", 
            int socks_port = 9050, 
            const std::string& version = "14.5.4");
    ~Network();

    void connect(const std::string& own_onion_address, const std::vector<uint8_t>& own_fingerprint, 
                 const std::string& peer_onion_address, const std::vector<uint8_t>& peer_fingerprint);
    void disconnect();       // close the socket + send 0x05 (internal usage io_loop/destructor)
    void close_connection(); // close the socket WITHOUT sending 0x05 (to be called from ProtocolHandler)
    bool flush_outgoing(int timeout_ms = 500);
    bool isConnected() const;

    void sendMessage(const std::vector<uint8_t>& payload, uint16_t message_type);
    bool receiveMessage(std::vector<uint8_t>& out_payload, uint16_t& out_message_type);
    std::string get_onion() const;

    std::vector<uint8_t> format_message(const std::vector<uint8_t>& payload, uint16_t message_type);

private:
    int tor_socks_port;
    int tor_service_port;
    
    std::unique_ptr<TorManager> tor_manager;

    socket_t server_socket;
    socket_t client_socket; 

    std::atomic<bool> connected;
    std::atomic<bool> is_running;

    std::string peer_onion_address;
    std::vector<uint8_t> peer_fingerprint;

    std::queue<std::vector<uint8_t>> outgoing_messages;
    std::mutex outgoing_mutex;

    std::queue<std::vector<uint8_t>> incoming_messages;
    std::mutex incoming_mutex;

    std::thread listener_thread;
    std::thread io_thread;

    void listener_loop();
    void io_loop();
    
    void init_sockets();
    void cleanup_sockets();

    bool socks5_connect(const std::string& onion_host, int port);
};

#endif // LIBNETWORK_HPP