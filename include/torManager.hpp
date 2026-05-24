#ifndef TOR_MANAGER_HPP
#define TOR_MANAGER_HPP

#include <string>
#include <filesystem>
#include <vector>

namespace fs = std::filesystem;

class TorManager {
public:
    /**
     * @brief Constructor 
     * @param service_port local port to expose the hidden service (default: 8080)
     * @param install_dir Directory where Tor is installed (e.g., "./tor_bin")
     * @param socks_port Internal SOCKS5 port (default: 9050)
     * @param version Version of Tor to download if not present
     */
    TorManager(int service_port = 8080, 
               const std::string& install_dir = "tor", 
               int socks_port = 9050,
               const std::string& version = "14.5.4");

    ~TorManager();

    bool start();
    void stop();

    std::string getOnionAddress() const { return onion_address; }
    bool isRunning() const;

private:
    // Parameters
    int service_port;
    int socks_port;
    std::string version;
    fs::path root_path;
    fs::path executable_path;

    // state
    long long tor_pid = -1; // use long long to accommodate large PIDs on some platforms (fuck you, Windows!)
    std::string onion_address;

    // final logic
    bool ensureTorInstalled();
    std::string getDownloadUrl();
    bool downloadAndExtract(const std::string& url);
    bool createTorrc();
    bool waitForOnionAddress(int timeout_sec = 60);
    
    // Abstraction OS
    void killProcess(long long pid);
    long long launchProcess(const std::vector<std::string>& args);
};

#endif