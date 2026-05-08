#ifndef PROTOCOLHANDLER_HPP
#define PROTOCOLHANDLER_HPP

#include "libNetwork.hpp"
#include "libCrypto.hpp"
#include "libCryptoSession.hpp"
#include "libHost.hpp"
#include <memory>
#include <string>
#include <vector>
#include <queue>
#include <fstream>
#include <filesystem>
#include "MemorySecurity.hpp"

class ProtocolHandler {
public:
    enum class Role { INITIATOR, RESPONDER, NONE };
    enum class State {
        DISCONNECTED,
        AWAITING_RESPONSE,
        AWAITING_CHALLENGE_A,
        AWAITING_CHALLENGE_B_AND_RESP_A,
        AWAITING_RESP_B,
        ESTABLISHED,
        ERROR_STATE
    };

    ProtocolHandler(Network* net, CryptoManager* crypto, HostManager* hosts);
    
    // Initiates the connection to a peer
    void start_handshake(const std::string& peer_onion);

    // Must be called repeatedly in the main loop to process network queues
    void tick();

    State get_state() const { return current_state; }
    CryptoManager* get_crypto() const { return crypto_manager; }

    // Chat functionality
    void send_chat(const std::string& msg);
    bool receive_chat(std::string& out_msg);

    // Disconnect from the current peer
    void disconnect();

    void ping(); // Send a ping message to the peer

    // File transfer functionality
    void initiate_file_transfer(const std::string& file_path);
    void respond_to_file_transfer(bool accept);

private:
    Network* network;
    CryptoManager* crypto_manager;
    HostManager* host_manager;
    std::unique_ptr<CryptoSession> session;
    
    Role role = Role::NONE;
    State current_state = State::DISCONNECTED;

    std::string peer_onion;
    std::vector<uint8_t> peer_pub_key;

    SecureVector my_nonce;
    SecureVector peer_nonce;

    std::queue<std::string> incoming_chats;

    // File transfer state
    struct FileTransfer {
        bool active = false;
        std::string filename;
        uint64_t size = 0;
        uint64_t processed = 0;
        std::fstream stream;
        bool is_sending = false;
    } current_transfer;

    void process_message(uint16_t type, const std::vector<uint8_t>& payload);
    
    void handle_type_01(const std::vector<uint8_t>& payload);
    void handle_type_02(const std::vector<uint8_t>& payload);
    void handle_type_03(const std::vector<uint8_t>& payload);
    void handle_type_04(const std::vector<uint8_t>& payload);
    void handle_type_05(const std::vector<uint8_t>& payload);
    void handle_type_06(const std::vector<uint8_t>& payload);
    void handle_type_07(const std::vector<uint8_t>& payload);
    void handle_type_08(const std::vector<uint8_t>& payload);
    void handle_type_09(const std::vector<uint8_t>& payload);
    void handle_type_0A(const std::vector<uint8_t>& payload);
    void handle_type_0B(const std::vector<uint8_t>& payload);
    void handle_type_0C(const std::vector<uint8_t>& payload);

    void send_next_chunk();
    void cleanup_transfer();

    SecureVector generate_nonce();
    void send_connection_request(uint16_t type); // Sends own onion and public key
    
    void reset_state(); // Full reset of all session parameters
    void fail(const std::string& reason);
};

#endif // PROTOCOLHANDLER_HPP
