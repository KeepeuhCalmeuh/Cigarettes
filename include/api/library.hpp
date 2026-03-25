#include <stdio.h>
#include <iostream>
#include "libHost.hpp"
#include "libCrypto.hpp"
#include "libConfig.hpp"
#include "libNetwork.hpp"
#include "ProtocolHandler.hpp"
#include "CommandHandler.hpp"
#include <atomic>

#ifdef _WIN32
  #ifdef BUILDING_LIB
    #define CIG_EXPORT __declspec(dllexport)
  #else
    #define CIG_EXPORT __declspec(dllimport)
  #endif
#else
  #ifdef BUILDING_LIB
    #define CIG_EXPORT __attribute__((visibility("default")))
  #else
    #define CIG_EXPORT
  #endif
#endif

using namespace std;

class CIG_EXPORT Cigarettes {
public:
    Cigarettes(std::string passphrase);

    Config config; // config instance to manage configuration settings
    HostManager hostManager; // HostManager instance to manage the known hosts and their fingerprints
    CryptoManager cryptoManager; // CryptoManager instance to handle cryptographic operations
    Network network; // Network instance to handle TOR network communications
    ProtocolHandler protocol; // ProtocolHandler instance to handle communication logic
    CommandHandler command; // CommandHandler instance to handle user commands
    std::atomic<bool> keep_running{true}; // Flag to track if the application should keep running

    void add_host(const string& fingerprint, const string& onion, const string& nickname);
    void delete_host(const string& fingerprint);
    
    void tick();
    bool receive_chat(string& out_msg);
    void process_command(const string& cmd);
    
    string get_onion() const;
    string get_fingerprint() const;

    void test_function();

private:
    
};