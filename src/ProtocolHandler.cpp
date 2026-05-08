#include "ProtocolHandler.hpp"
#include <iostream>
#include <openssl/rand.h>

ProtocolHandler::ProtocolHandler(Network* net, CryptoManager* crypto, HostManager* hosts)
    : network(net), crypto_manager(crypto), host_manager(hosts) {
}

void ProtocolHandler::start_handshake(const std::string& target_onion) {
    if (current_state != State::DISCONNECTED) return;
    
    this->peer_onion = target_onion;
    // We pass empty fingerprint/pubkey here, libNetwork just connects TCP
    network->connect("my_onion", {}, target_onion, {}); 
    
    role = Role::INITIATOR;
    send_connection_request(0x01);
    current_state = State::AWAITING_RESPONSE;
    std::cout << "[Protocol] Sent 0x01 Req. AWAITING_RESPONSE\n";
}

void ProtocolHandler::tick() {
    std::vector<uint8_t> payload;
    uint16_t type = 0;

    // Process all incoming messages
    while (network->receiveMessage(payload, type)) {
        // extract message type from first 8 bytes (assuming Network::format_message design)
        // Wait, libNetwork::receiveMessage doesn't parse it yet. 
        // We will do it here temporarily or in Network. Let's assume network->receiveMessage gave us full unparsed frame.
        // Format from format_message: 8 bytes TYPE, N bytes PAYLOAD, 8 bytes TIMESTAMP.
        // Let's manually parse it here:
        if (payload.size() < 16) continue;
        
        uint64_t msg_type_64 = 0;
        for (int i = 0; i < 8; ++i) {
            msg_type_64 |= ((uint64_t)payload[i] << (i * 8));
        }
        type = (uint16_t)msg_type_64;
        
        std::vector<uint8_t> actual_payload(payload.begin() + 8, payload.end() - 8);
        process_message(type, actual_payload);
    }
}
/*
Message format:
[4 bytes total_body_len][8 bytes type][payload][8 bytes timestamp]

Message type : 
0x01: Initial connection request
0x02: Response to connection request (includes responder's onion and pubkey)
0x03: Challenge/response messages for authentication
0x04: Encrypted chat message
0x05: Disconnect notification
0x06: Rejection message (unknown fingerprint)
0x07: ping
0x08: pong
0x09: file transfer initialisation messages
0x0A: file transfer accept/reject message
0x0B: file transfer data chunk
0x0C: file transfer completion message
*/
void ProtocolHandler::process_message(uint16_t type, const std::vector<uint8_t>& payload) {
    switch (type) {
        case 0x01: handle_type_01(payload); break;
        case 0x02: handle_type_02(payload); break;
        case 0x03: handle_type_03(payload); break;
        case 0x04: handle_type_04(payload); break;
        case 0x05: handle_type_05(payload); break;
        case 0x06: handle_type_06(payload); break;
        case 0x07: handle_type_07(payload); break;
        case 0x08: handle_type_08(payload); break;
        case 0x09: handle_type_09(payload); break;
        case 0x0A: handle_type_0A(payload); break;
        case 0x0B: handle_type_0B(payload); break;
        case 0x0C: handle_type_0C(payload); break;
        default: std::cerr << "[Protocol] Unknown message type: " << std::hex << type << std::dec << "\n"; break;
    }
}

void ProtocolHandler::send_connection_request(uint16_t type) {
    std::string onion = network->get_onion(); 
    if (onion.empty()) onion = "unknown.onion"; // Fallback if Tor manager hasn't synced reading

    std::vector<uint8_t> pub_bytes = crypto_manager->get_public_bytes();
    
    std::vector<uint8_t> out;
    out.push_back((uint8_t)onion.length());
    for (char c : onion) out.push_back(c);
    
    uint16_t pub_len = pub_bytes.size();
    out.push_back(pub_len & 0xFF);
    out.push_back((pub_len >> 8) & 0xFF);
    out.insert(out.end(), pub_bytes.begin(), pub_bytes.end());
    
    // Sign the previous data
    std::vector<uint8_t> signature = crypto_manager->sign_data(out);
    
    uint16_t sig_len = signature.size();
    out.push_back(sig_len & 0xFF);
    out.push_back((sig_len >> 8) & 0xFF);
    out.insert(out.end(), signature.begin(), signature.end());
    
    network->sendMessage(out, type);
}

void ProtocolHandler::handle_type_01(const std::vector<uint8_t>& payload) {
    if (current_state != State::DISCONNECTED) return;
    
    // Parse Payload
    if (payload.empty()) return fail("Empty 0x01");
    uint8_t onion_len = payload[0];
    size_t offset = 1;
    
    if (payload.size() < offset + onion_len) return fail("Invalid 0x01 onion len");
    peer_onion = std::string(payload.begin() + offset, payload.begin() + offset + onion_len);
    offset += onion_len;
    
    if (payload.size() < offset + 2) return fail("Invalid 0x01 pub_len");
    uint16_t pub_len = payload[offset] | (payload[offset+1] << 8);
    offset += 2;
    
    if (payload.size() < offset + pub_len) return fail("Invalid 0x01 pubkey len");
    peer_pub_key = std::vector<uint8_t>(payload.begin() + offset, payload.begin() + offset + pub_len);
    offset += pub_len;
    
    if (payload.size() < offset + 2) return fail("Invalid 0x01 sig_len");
    uint16_t sig_len = payload[offset] | (payload[offset+1] << 8);
    offset += 2;
    
    if (payload.size() < offset + sig_len) return fail("Invalid 0x01 signature len");
    std::vector<uint8_t> signature(payload.begin() + offset, payload.begin() + offset + sig_len);
    
    std::vector<uint8_t> signed_data(payload.begin(), payload.begin() + (offset - 2));
    if (!crypto_manager->verify_signature(signed_data, signature, peer_pub_key)) {
        return fail("Invalid 0x01 signature");
    }
    
    // Verify fingerprint
    std::string fingerprint = CryptoManager::calculate_fingerprint(peer_pub_key);
    nlohmann::json host_info;
    if (!host_manager->get_host(fingerprint, host_info)) {
        std::cout << "[Protocol] Denied: Peer fingerprint unknown: " << fingerprint << "\n";
        network->sendMessage({}, 0x06); // Send REJECTION
        network->flush_outgoing(500);
        network->close_connection();
        reset_state();
        return;
    }

    std::cout << "[Protocol] Received 0x01 from known host: " << host_info["nickname"].get<std::string>() 
              << " (" << peer_onion << ")\n";
    
    role = Role::RESPONDER;
    send_connection_request(0x02); // Send Response
    current_state = State::AWAITING_CHALLENGE_A;
    std::cout << "[Protocol] Sent 0x02. AWAITING_CHALLENGE_A\n";
}

void ProtocolHandler::handle_type_02(const std::vector<uint8_t>& payload) {
    if (role != Role::INITIATOR || current_state != State::AWAITING_RESPONSE) return;

    // Parse Payload
    if (payload.empty()) return fail("Empty 0x02");
    uint8_t onion_len = payload[0];
    size_t offset = 1;
    
    if (payload.size() < offset + onion_len) return fail("Invalid 0x02 onion len");
    offset += onion_len;
    
    if (payload.size() < offset + 2) return fail("Invalid 0x02 pub_len");
    uint16_t pub_len = payload[offset] | (payload[offset+1] << 8);
    offset += 2;

    if (payload.size() < offset + pub_len) return fail("Invalid 0x02 pubkey len");
    peer_pub_key = std::vector<uint8_t>(payload.begin() + offset, payload.begin() + offset + pub_len);
    offset += pub_len;

    if (payload.size() < offset + 2) return fail("Invalid 0x02 sig_len");
    uint16_t sig_len = payload[offset] | (payload[offset+1] << 8);
    offset += 2;

    if (payload.size() < offset + sig_len) return fail("Invalid 0x02 signature len");
    std::vector<uint8_t> signature(payload.begin() + offset, payload.begin() + offset + sig_len);

    std::vector<uint8_t> signed_data(payload.begin(), payload.begin() + (offset - 2));
    if (!crypto_manager->verify_signature(signed_data, signature, peer_pub_key)) {
        return fail("Invalid 0x02 signature");
    }

    // Verify fingerprint
    std::string fingerprint = CryptoManager::calculate_fingerprint(peer_pub_key);
    nlohmann::json host_info;
    if (!host_manager->get_host(fingerprint, host_info)) {
        std::cout << "[Protocol] Denied: Peer fingerprint unknown: " << fingerprint << "\n";
        network->sendMessage({}, 0x06); // Send REJECTION
        network->flush_outgoing(500);
        network->close_connection();
        reset_state();
        return;
    }

    std::cout << "[Protocol] Received 0x02 from known host: " << host_info["nickname"].get<std::string>() << "\n";
    std::cout << "[Protocol] Sending Challenge A...\n";

    // Send Challenge 0x03 A
    my_nonce = generate_nonce();
    network->sendMessage(std::vector<uint8_t>(my_nonce.begin(), my_nonce.end()), 0x03);
    
    current_state = State::AWAITING_CHALLENGE_B_AND_RESP_A;
}


void ProtocolHandler::handle_type_03(const std::vector<uint8_t>& payload) {
    if (role == Role::RESPONDER && current_state == State::AWAITING_CHALLENGE_A) {
        if (payload.size() != 32) return fail("Invalid Challenge A size");
        peer_nonce = SecureVector(payload.begin(), payload.end());
        
        std::cout << "[Protocol] Received Challenge A. Sending Challenge B + Resp A...\n";
        
        // Sign peer nonce
        std::vector<uint8_t> sigA = crypto_manager->sign_data(std::vector<uint8_t>(peer_nonce.begin(), peer_nonce.end()));
        
        // Gen my nonce
        my_nonce = generate_nonce();
        
        // payload: [my_nonce 32] [sig_len 2] [sigA]
        std::vector<uint8_t> out(my_nonce.begin(), my_nonce.end());
        uint16_t sigA_len = sigA.size();
        out.push_back(sigA_len & 0xFF);
        out.push_back((sigA_len >> 8) & 0xFF);
        out.insert(out.end(), sigA.begin(), sigA.end());
        
        network->sendMessage(out, 0x03);
        current_state = State::AWAITING_RESP_B;
    }
    else if (role == Role::INITIATOR && current_state == State::AWAITING_CHALLENGE_B_AND_RESP_A) {
        // payload: [peer_nonce 32] [sig_len 2] [sigA]
        if (payload.size() < 34) return fail("Invalid Challenge B");
        
        peer_nonce = SecureVector(payload.begin(), payload.begin() + 32);
        uint16_t sigA_len = payload[32] | (payload[33] << 8);
        if (payload.size() != 34 + sigA_len) return fail("Invalid SigA len");
        
        std::vector<uint8_t> sigA(payload.begin() + 34, payload.end());
        
        if (!crypto_manager->verify_signature(std::vector<uint8_t>(my_nonce.begin(), my_nonce.end()), sigA, peer_pub_key)) {
            return fail("Signature A invalid!");
        }
        
        std::cout << "[Protocol] verified Peer B identity!\n";
        
        // Send Resp B
        std::vector<uint8_t> sigB = crypto_manager->sign_data(std::vector<uint8_t>(peer_nonce.begin(), peer_nonce.end()));
        network->sendMessage(sigB, 0x03);
        
        // Setup session
        session = std::make_unique<CryptoSession>(
            crypto_manager->get_private_key(),
            peer_pub_key,
            my_nonce,   // nonce_A
            peer_nonce  // nonce_B
        );
        current_state = State::ESTABLISHED;
        std::cout << "[Protocol] Session ESTABLISHED (Initiator)!\n";
    }
    else if (role == Role::RESPONDER && current_state == State::AWAITING_RESP_B) {
        // payload is sigB
        if (!crypto_manager->verify_signature(std::vector<uint8_t>(my_nonce.begin(), my_nonce.end()), payload, peer_pub_key)) {
            return fail("Signature B invalid!");
        }
        
        std::cout << "[Protocol] verified Peer A identity!\n";
        
        session = std::make_unique<CryptoSession>(
            crypto_manager->get_private_key(),
            peer_pub_key,
            peer_nonce, 
            my_nonce    
        );
        current_state = State::ESTABLISHED;
        std::cout << "[Protocol] Session ESTABLISHED (Responder)!\n";
    }
}

void ProtocolHandler::handle_type_04(const std::vector<uint8_t>& payload) {
    if (current_state != State::ESTABLISHED || !session) return;
    
    std::string decrypted = session->decrypt(payload);
    if (!decrypted.empty()) {
        incoming_chats.push(decrypted);
    }
}

void ProtocolHandler::handle_type_05(const std::vector<uint8_t>& payload) {
    std::cout << "[Protocol] Received 0x05 disconnect notification. Resetting...\n";
    network->close_connection(); // close properly without sending 0x05
    reset_state();
    std::cout << "[Protocol] Ready for a new connection.\n";
}


void ProtocolHandler::handle_type_06(const std::vector<uint8_t>& /*payload*/) {
    std::cout << "[Protocol] Connection REJECTED by peer (Unknown Fingerprint).\n";
    network->close_connection();
    reset_state();
}

// Handle PING
void ProtocolHandler::handle_type_07(const std::vector<uint8_t>& payload) {
    if (current_state != State::ESTABLISHED || !session) return;
    
    try {
        // Just decrypt and re-encrypt the same payload as a PONG response. The initiator will measure RTT based on this.
        std::string plaintext = session->decrypt(payload);
        network->sendMessage(session->encrypt(plaintext), 0x08);
    } catch (const std::exception& e) {
        std::cerr << "[Protocol] Invalid PING payload, ignoring: " << e.what() << "\n";
    }
}

// Handle PONG
void ProtocolHandler::handle_type_08(const std::vector<uint8_t>& payload) {
    if (current_state != State::ESTABLISHED || !session) return;
    
    std::string decrypted = session->decrypt(payload);
    if (decrypted.empty()) return;

    try {
        long long sent_time = std::stoll(decrypted);
        auto now = std::chrono::steady_clock::now();
        auto duration = std::chrono::duration_cast<std::chrono::milliseconds>(now.time_since_epoch());
        long long current_time = duration.count();
        
        long long rtt = current_time - sent_time;
        std::cout << "[Protocol] Received PONG. RTT: " << rtt << "ms\n> ";
        std::cout.flush();
    } catch (...) {
        std::cerr << "[Protocol] Failed to parse PONG timestamp\n> ";
        std::cout.flush();
    }
}

void ProtocolHandler::handle_type_09(const std::vector<uint8_t>& payload) {
    if (current_state != State::ESTABLISHED || !session) return;
    
    std::string decrypted = session->decrypt(payload);
    if (decrypted.empty()) return;

    size_t pipe_pos = decrypted.find('|');
    if (pipe_pos == std::string::npos) return;

    std::string size_str = decrypted.substr(0, pipe_pos);
    std::string raw_name = decrypted.substr(pipe_pos + 1);
    current_transfer.filename = std::filesystem::path(raw_name).filename().string();

    if (current_transfer.filename.empty() || current_transfer.filename == "." || current_transfer.filename == "..") {
        std::cerr << "[Protocol] Rejected: invalid filename from peer.\n";
        network->sendMessage(session->encrypt("Reject_file_transfer"), 0x0A);
        cleanup_transfer();
        return;
    }

    current_transfer.active = true;
    current_transfer.filename = filename;
    current_transfer.size = std::stoull(size_str);
    current_transfer.processed = 0;
    current_transfer.is_sending = false;

    std::cout << "\n[Protocol] Incoming file transfer: " << filename << " (" << current_transfer.size << " bytes)\n";
    std::cout << "[Protocol] Type /accept or /reject to respond.\n> ";
    std::cout.flush();
}

void ProtocolHandler::handle_type_0A(const std::vector<uint8_t>& payload) {
    if (current_state != State::ESTABLISHED || !session || !current_transfer.active || !current_transfer.is_sending) return;

    std::string decrypted = session->decrypt(payload);
    if (decrypted == "Accept_file_transfer") {
        std::cout << "[Protocol] Peer accepted file transfer. Starting upload...\n";
        send_next_chunk();
    } else {
        std::cout << "[Protocol] Peer rejected file transfer.\n> ";
        std::cout.flush();
        cleanup_transfer();
    }
}

void ProtocolHandler::handle_type_0B(const std::vector<uint8_t>& payload) {
    if (current_state != State::ESTABLISHED || !session || !current_transfer.active || current_transfer.is_sending) return;

    std::vector<uint8_t> data = session->decrypt_bytes(payload);
    if (data.empty() && !payload.empty()) return;

    if (!current_transfer.stream.is_open()) {
        std::filesystem::create_directories("received_files");
        std::string path = "received_files/" + current_transfer.filename;
        current_transfer.stream.open(path, std::ios::out | std::ios::binary);
    }

    if (current_transfer.stream.is_open()) {
        current_transfer.stream.write((char*)data.data(), data.size());
        current_transfer.processed += data.size();
    }
}

void ProtocolHandler::handle_type_0C(const std::vector<uint8_t>& payload) {
    if (current_state != State::ESTABLISHED || !session || !current_transfer.active || current_transfer.is_sending) return;

    std::string decrypted = session->decrypt(payload);
    if (decrypted.empty()) return;

    size_t pipe_pos = decrypted.find('|');
    if (pipe_pos == std::string::npos) return;

    uint64_t final_size = std::stoull(decrypted.substr(0, pipe_pos));
    
    if (current_transfer.processed == final_size) {
        std::cout << "\n[Protocol] File transfer complete: " << current_transfer.filename << " received successfully.\n> ";
    } else {
        std::cout << "\n[Protocol] File transfer error: Size mismatch (" << current_transfer.processed << " / " << final_size << ")\n> ";
    }
    std::cout.flush();
    cleanup_transfer();
}

void ProtocolHandler::initiate_file_transfer(const std::string& file_path) {
    if (current_state != State::ESTABLISHED || !session) {
        std::cout << "[Protocol] Error: Not connected to any peer.\n";
        return;
    }

    if (current_transfer.active) {
        std::cout << "[Protocol] Error: A transfer is already in progress.\n";
        return;
    }

    std::filesystem::path p(file_path);
    if (!std::filesystem::exists(p)) {
        std::cout << "[Protocol] Error: File does not exist.\n";
        return;
    }

    current_transfer.active = true;
    current_transfer.is_sending = true;
    current_transfer.filename = p.filename().string();
    current_transfer.size = std::filesystem::file_size(p);
    current_transfer.processed = 0;
    current_transfer.stream.open(file_path, std::ios::in | std::ios::binary);

    if (!current_transfer.stream.is_open()) {
        std::cout << "[Protocol] Error: Could not open file.\n";
        cleanup_transfer();
        return;
    }

    std::string init_payload = std::to_string(current_transfer.size) + "|" + current_transfer.filename;
    network->sendMessage(session->encrypt(init_payload), 0x09);
    
    std::cout << "[Protocol] Sent file transfer request: " << current_transfer.filename << " (" << current_transfer.size << " bytes)\n";
}

void ProtocolHandler::respond_to_file_transfer(bool accept) {
    if (current_state != State::ESTABLISHED || !session || !current_transfer.active || current_transfer.is_sending) return;

    if (accept) {
        network->sendMessage(session->encrypt("Accept_file_transfer"), 0x0A);
        std::cout << "[Protocol] Accept sent. Waiting for data...\n";
    } else {
        network->sendMessage(session->encrypt("Reject_file_transfer"), 0x0A);
        std::cout << "[Protocol] Reject sent.\n";
        cleanup_transfer();
    }
}

void ProtocolHandler::send_next_chunk() {
    if (!current_transfer.active || !current_transfer.is_sending || !current_transfer.stream.is_open()) return;

    char buffer[4096];

    while (true) {
        current_transfer.stream.read(buffer, sizeof(buffer));
        std::streamsize bytes_read = current_transfer.stream.gcount();

        if (bytes_read <= 0) break;

        std::vector<uint8_t> chunk(buffer, buffer + bytes_read);
        network->sendMessage(session->encrypt_bytes(chunk), 0x0B);
        current_transfer.processed += bytes_read;

        if (current_transfer.stream.eof()) {
            std::string done_payload = std::to_string(current_transfer.size) + "|" + current_transfer.filename;
            network->sendMessage(session->encrypt(done_payload), 0x0C);
            std::cout << "[Protocol] File transfer completed successfully.\n> ";
            std::cout.flush();
            cleanup_transfer();
            break;
        }
    }
}

void ProtocolHandler::cleanup_transfer() {
    if (current_transfer.stream.is_open()) {
        current_transfer.stream.close();
    }
    current_transfer.active = false;
    current_transfer.filename.clear();
    current_transfer.size = 0;
    current_transfer.processed = 0;
    current_transfer.is_sending = false;
}

void ProtocolHandler::disconnect() {
    if (current_state != State::DISCONNECTED && current_state != State::ERROR_STATE) {
        std::cout << "[Protocol] Sending 0x05 disconnect notification...\n";
        network->sendMessage({}, 0x05); // Notify peer before disconnecting
        network->flush_outgoing(500);   // Wait up to 500ms for message to hit the wire
    }
    network->close_connection(); // close the socket without sending 0x05
    reset_state();
    std::cout << "[Protocol] Disconnected.\n";
}

void ProtocolHandler::send_chat(const std::string& msg) {
    if (current_state != State::ESTABLISHED || !session) return;
    std::vector<uint8_t> cipher = session->encrypt(msg);
    network->sendMessage(cipher, 0x04);
}

bool ProtocolHandler::receive_chat(std::string& out_msg) {
    if (!incoming_chats.empty()) {
        out_msg = incoming_chats.front();
        incoming_chats.pop();
        return true;
    }
    return false;
}

SecureVector ProtocolHandler::generate_nonce() {
    SecureVector nonce(32);
    RAND_bytes(nonce.data(), 32);
    return nonce;
}

void ProtocolHandler::fail(const std::string& reason) {
    std::cerr << "[Protocol] FAILED: " << reason << "\n";
    current_state = State::ERROR_STATE;
    network->close_connection(); // Drop connection without sending 0x05
}

void ProtocolHandler::reset_state() {
    current_state = State::DISCONNECTED;
    role = Role::NONE;
    session.reset();
    peer_onion.clear();
    peer_pub_key.clear();
    my_nonce.clear();
    peer_nonce.clear();
    // clear the incoming chats queue
    while (!incoming_chats.empty()) incoming_chats.pop();
}

void ProtocolHandler::ping() {
    if (current_state != State::ESTABLISHED || !session) return;

    auto now = std::chrono::steady_clock::now();
    uint64_t timestamp = std::chrono::duration_cast<std::chrono::milliseconds>(now.time_since_epoch()).count();
    
    std::string ts_str = std::to_string(timestamp);
    std::vector<uint8_t> encrypted_ts = session->encrypt(ts_str);
    
    network->sendMessage(encrypted_ts, 0x07);
    std::cout << "[Protocol] Sent PING...\n";
}
