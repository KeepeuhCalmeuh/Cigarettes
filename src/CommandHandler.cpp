#include "CommandHandler.hpp"
#include <iostream>

CommandHandler::CommandHandler(ProtocolHandler* protocol, HostManager* hosts, std::atomic<bool>& keep_running)
    : protocol(protocol), host_manager(hosts), keep_running(keep_running) {}

bool CommandHandler::process(const std::string& input) {
    if (input.empty()) return false;

    if (input[0] != '/') {
        // Not a command: treat as a chat message
        if (protocol->get_state() == ProtocolHandler::State::ESTABLISHED) {
            protocol->send_chat(input);
        } else {
            std::cout << "[! Not connected yet]\n> ";
            std::cout.flush();
        }
        return false;
    }

    // Extract command name and arguments
    auto space_pos      = input.find(' ');
    std::string cmd     = input.substr(0, space_pos);
    std::string args    = (space_pos != std::string::npos) ? input.substr(space_pos + 1) : "";

    if      (cmd == "/exit")       handleExit(args);
    else if (cmd == "/help")       handleHelp(args);
    else if (cmd == "/disconnect") handleDisconnect(args);
    else if (cmd == "/connect")    handleConnect(args);
    else if (cmd == "/rename")     handleRename(args);
    else if (cmd == "/addHost" || cmd == "/ad") handleAddHost(args);
    else if (cmd == "/removehost" || cmd == "/rmh") handleRemoveHost(args);
    else if (cmd == "/listHosts" || cmd == "/ls") handleListHosts(args);
    else if (cmd == "/reset_key")   handleResetKey(args);
    else if (cmd == "/ping")        handlePing(args);
    else if (cmd == "/filetransfer") handleFileTransfer(args);
    else if (cmd == "/accept")      handleAccept(args);
    else if (cmd == "/reject")      handleReject(args);
    else {
        std::cout << "[!] Unknown command: " << cmd << ". Type /help for the list of commands.\n> ";
        std::cout.flush();
    }

    return true;
}

// ── Private handlers ──────────────────────────────────────────────────────────

void CommandHandler::handleExit(const std::string& /*args*/) {
    //if connected, disconnect first
    if (protocol->get_state() == ProtocolHandler::State::ESTABLISHED) {
        protocol->disconnect();
    }   
    
    keep_running = false;
}

void CommandHandler::handleHelp(const std::string& /*args*/) {
    std::cout << "Available commands:\n"
              << "  /connect <onion>              - Connect to a peer by its .onion address\n"
              << "  /disconnect                   - Disconnect from the current peer\n"
              << "  /addHost <onion> <fp> [nick]  - Add a host to known hosts (alias: /ad)\n"
              << "  /removehost <fp>              - Remove a peer from the host list (alias: /rmh)\n"
              << "  /rename <fp> <new_name>       - Rename a peer in known hosts\n"
              << "  /listHosts                    - List all known hosts (alias: /ls)\n"
              << "  /ping                         - Send a ping to the current peer and display the RTT\n"
              << "  /filetransfer <path>          - Send a file to the current peer\n"
              << "  /accept                       - Accept an incoming file transfer\n"
              << "  /reject                       - Reject an incoming file transfer\n"
              << "  /exit                         - Exit the application\n"
              << "  /help                         - Show this help message\n"
              << "Otherwise, just type and hit Enter to send a chat message.\n> ";
    std::cout.flush();
}

void CommandHandler::handleDisconnect(const std::string& /*args*/) {
    protocol->disconnect();
    std::cout << "Disconnected from peer.\n> ";
    std::cout.flush();
}

void CommandHandler::handleConnect(const std::string& args) {
    if (args.empty()) {
        std::cout << "[!] Usage: /connect <onion>\n> ";
        std::cout.flush();
        return;
    }
    protocol->start_handshake(args);
    std::cout << "Connecting to " << args << "...\n> ";
    std::cout.flush();
}

void CommandHandler::handleRename(const std::string& args) {
    auto space_pos = args.find(' ');
    if (space_pos == std::string::npos) {
        std::cout << "[!] Usage: /rename <fingerprint> <new_name>\n> ";
        std::cout.flush();
        return;
    }
    std::string fp = args.substr(0, space_pos);
    std::string nick = args.substr(space_pos + 1);

    std::string onion = host_manager->get_onion(fp);
    if (onion.empty()) {
        std::cout << "[!] Host not found: " << fp << "\n> ";
        std::cout.flush();
        return;
    }

    host_manager->upsert_host(fp, onion, nick);
    std::cout << "[+] Host renamed to " << nick << "\n> ";
    std::cout.flush();
}

void CommandHandler::handleAddHost(const std::string& args) {
    // Expected: <onion> <fp> [nick]
    auto space1 = args.find(' ');
    if (space1 == std::string::npos) {
        std::cout << "[!] Usage: /addHost <onion> <fingerprint> [nickname]\n> ";
        std::cout.flush();
        return;
    }

    std::string onion = args.substr(0, space1);
    std::string rest = args.substr(space1 + 1);
    
    auto space2 = rest.find(' ');
    std::string fp, nick;
    if (space2 == std::string::npos) {
        fp = rest;
        nick = "Unknown";
    } else {
        fp = rest.substr(0, space2);
        nick = rest.substr(space2 + 1);
    }

    host_manager->upsert_host(fp, onion, nick);
    std::cout << "[+] Host added: " << nick << " (" << fp.substr(0, 8) << "...)\n> ";
    std::cout.flush();
}

void CommandHandler::handleRemoveHost(const std::string& args) {
    if (args.empty()) {
        std::cout << "[!] Usage: /removehost <fingerprint>\n> ";
        std::cout.flush();
        return;
    }
    host_manager->delete_host(args);
    std::cout << "[-] Host removed.\n> ";
    std::cout.flush();
}

void CommandHandler::handleListHosts(const std::string& /*args*/) {
    host_manager->list_hosts();
    std::cout << "> ";
    std::cout.flush();
}

void CommandHandler::handleResetKey(const std::string& args) {
    std::cout << "[!] WARNING: Resetting your key will PERMANENTLY CHANGE your onion address and fingerprint.\n";
    std::cout << "    Your peers will no longer be able to reach you at your current address.\n";
    std::cout.flush();

    try {
        protocol->get_crypto()->reset_key(args);
        std::cout << "[+] Identity reset successful!\n";
        std::cout << "[+] New fingerprint: " << protocol->get_crypto()->get_fingerprint() << "\n";
        std::cout << "[!] IMPORTANT: You MUST restart the application for the changes to take effect on the Tor network.\n";
        std::cout << "[!] Exiting application...\n";
        keep_running = false;
    } catch (const std::exception& e) {
        std::cerr << "[!] Error during key reset: " << e.what() << "\n> ";
    }
    std::cout.flush();
}

void CommandHandler::handlePing(const std::string& args) {
    protocol->ping();
    std::cout << "> ";
    std::cout.flush();
}
void CommandHandler::handleFileTransfer(const std::string& args) {
    if (args.empty()) {
        std::cout << "[!] Usage: /filetransfer <file_path>\n> ";
        std::cout.flush();
        return;
    }
    protocol->initiate_file_transfer(args);
    std::cout << "> ";
    std::cout.flush();
}

void CommandHandler::handleAccept(const std::string& /*args*/) {
    protocol->respond_to_file_transfer(true);
    std::cout << "> ";
    std::cout.flush();
}

void CommandHandler::handleReject(const std::string& /*args*/) {
    protocol->respond_to_file_transfer(false);
    std::cout << "> ";
    std::cout.flush();
}
