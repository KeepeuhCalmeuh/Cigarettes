#include "libNetwork.hpp"
#include "libCrypto.hpp"
#include "ProtocolHandler.hpp"
#include "CommandHandler.hpp"
#include "libConfig.hpp"
#include "libHost.hpp"
#include <iostream>
#include <thread>
#include <string>
#include <atomic>
#include <queue>
#include <mutex>
#include <chrono>

std::queue<std::string> user_inputs;
std::mutex input_mutex;
std::atomic<bool> keep_running{true};

void input_thread() {
    std::string line;
    while (keep_running) {
        if (!std::getline(std::cin, line)) {
            break; // EOF
        }
        std::lock_guard<std::mutex> lock(input_mutex);
        user_inputs.push(line);
    }
}

int main(int argc, char* argv[]) {
    Config config;
    int service_port = config.TOR_SERVICE_PORT;
    std::string install_dir = config.install_dir;
    int socks_port = config.socks_port;
    std::string version = config.version;

    // get passphrase from user
    std::string passphrase;
    std::cout << "Enter passphrase: ";
    std::cin >> passphrase;

    if (argc > 1) service_port = std::stoi(argv[1]);
    if (argc > 2) install_dir = argv[2];
    if (argc > 3) socks_port = std::stoi(argv[3]);

    try {
        std::cout << "[Info] Starting CryptoManager...\n";
        CryptoManager crypto(passphrase);
        std::cout << "[Info] My fingerprint: " << crypto.get_fingerprint() << "\n";

        std::cout << "[Info] Starting Tor Network on Hidden Service port " << service_port << "...\n";
        Network network(service_port, install_dir, socks_port, version);
        std::cout << "[Info] My onion address: " << network.get_onion() << "\n";

        HostManager hosts;
        ProtocolHandler protocol(&network, &crypto, &hosts);
        CommandHandler commands(&protocol, &hosts, keep_running);

        std::cout << R"(========================================================
_________ .__                            __    __                 
\_   ___ \|__| _________ _______   _____/  |__/  |_  ____   ______
/    \  \/|  |/ ___\__  \_  __ \_/ __ \   __\   __\/ __ \ /  ___/
\     \___|  / /_/  > __ \|  | \/\  ___/|  |  |  | \  ___/ \___ \ 
\______  /__\___  (____  /__|    \___  >__|  |__|  \___  >____  >
        \/  /_____/     \/            \/                \/     \/ 

        KeepeuhCalmeuh
========================================================
 Tor E2E P2P CLI - Type '/connect <onion>' to initiate.
 Type '/help' to see all commands.
 Type '/exit' to quit. Otherwise, just type and hit Enter.
========================================================
> )";

        std::thread cin_thread(input_thread);

        std::cout << "Ready !\n> ";
        std::cout.flush();
        while (keep_running) {
            protocol.tick();

            // Receive chats
            std::string inc_msg;
            while (protocol.receive_chat(inc_msg)) {
                std::cout << "\r[Peer]: " << inc_msg << "\n> ";
                std::cout.flush();
            }

            // Process user input
            std::string user_cmd;
            {
                std::lock_guard<std::mutex> lock(input_mutex);
                if (!user_inputs.empty()) {
                    user_cmd = user_inputs.front();
                    user_inputs.pop();
                }
            }

            if (!user_cmd.empty()) {
                commands.process(user_cmd);
                if (!keep_running) break;
            }

            std::this_thread::sleep_for(std::chrono::milliseconds(50));
        }

        std::cout << "\nExiting...\n";
        cin_thread.detach(); // detach because std::getline blocks on stdin

        //close the program
        return 0;

    } catch (const std::exception& e) {
        std::cerr << "Fatal Error: " << e.what() << std::endl;
        return 1;
    }

    return 0;
}