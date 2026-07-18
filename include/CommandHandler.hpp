#ifndef COMMAND_HANDLER_HPP
#define COMMAND_HANDLER_HPP

#include "ProtocolHandler.hpp"
#include "libHost.hpp"
#include <string>
#include <atomic>

class CommandHandler {
public:
    CommandHandler(ProtocolHandler* protocol, HostManager* hosts, std::atomic<bool>& keep_running);

    // Returns true if the input was a command (starting with '/'), false if it's a chat message.
    // Processes the command or message accordingly.
    bool process(const std::string& input);

private:
    ProtocolHandler* protocol;
    HostManager* host_manager;
    std::atomic<bool>& keep_running;

    void handleExit(const std::string& args);
    void handleHelp(const std::string& args);
    void handleDisconnect(const std::string& args);
    void handleConnect(const std::string& args);
    void handleRename(const std::string& args);
    void handleAddHost(const std::string& args);
    void handleRemoveHost(const std::string& args);
    void handleListHosts(const std::string& args);
    void handleResetKey(const std::string& args);
    void handlePing(const std::string& args);
    void handleFileTransfer(const std::string& args);
    void handleAccept(const std::string& args);
    void handleReject(const std::string& args);
};

#endif // COMMAND_HANDLER_HPP