#include "torManager.hpp"
#include <iostream>
#include <fstream>
#include <thread>
#include <chrono>
#include <cstdlib>

#ifdef _WIN32
    #include <windows.h>
    #define EXE_EXT ".exe"
#else
    #include <unistd.h>
    #include <sys/types.h>
    #include <sys/wait.h>
    #include <signal.h>
    #define EXE_EXT ""
#endif

static bool isExecutable(const fs::path& p) {
#ifdef _WIN32
    return fs::exists(p);
#else
    return fs::exists(p) && access(p.c_str(), X_OK) == 0;
#endif
}

static fs::path findExecutableInPath(const std::string& name) {
    const char* path_env = std::getenv("PATH");
    if (!path_env) return {};

#ifdef _WIN32
    const char path_sep = ';';
    const std::vector<std::string> extensions = {".exe", ".bat", ".cmd", ""};
#else
    const char path_sep = ':';
    const std::vector<std::string> extensions = {""};
#endif

    std::string path_str(path_env);
    size_t start = 0;
    while (start <= path_str.size()) {
        size_t end = path_str.find(path_sep, start);
        if (end == std::string::npos) end = path_str.size();
        std::string dir = path_str.substr(start, end - start);
        if (!dir.empty()) {
            for (const auto& ext : extensions) {
                fs::path candidate = fs::path(dir) / (name + ext);
                if (isExecutable(candidate)) return candidate;
            }
        }
        start = end + 1;
    }
    return {};
}

static bool testTorExecutable(const fs::path& path) {
#ifdef _WIN32
    std::string cmd = "\"" + path.string() + "\" --version >nul 2>&1";
#else
    std::string cmd = "\"" + path.string() + "\" --version >/dev/null 2>&1";
#endif
    return std::system(cmd.c_str()) == 0;
}

TorManager::TorManager(int port, const std::string& dir, int s_port, const std::string& ver)
    : service_port(port), socks_port(s_port), version(ver), root_path(fs::absolute(dir)) {
}

TorManager::~TorManager() {
    stop();
}

std::string TorManager::getDownloadUrl() {
    std::string os_str, arch_str = "x86_64";
#ifdef _WIN32
    os_str = "windows";
#elif __APPLE__
    os_str = "macos";
#else
    os_str = "linux";
#endif
    return "https://archive.torproject.org/tor-package-archive/torbrowser/" + version + 
           "/tor-expert-bundle-" + os_str + "-" + arch_str + "-" + version + 
           (os_str == "windows" ? ".zip" : ".tar.gz");
}

bool TorManager::ensureTorInstalled() {
    fs::path system_tor = findExecutableInPath("tor");
    if (!system_tor.empty()) {
        if (testTorExecutable(system_tor)) {
            executable_path = system_tor;
            std::cout << "[Tor] Using system Tor: " << executable_path << std::endl;
            return true;
        }
        std::cout << "[Tor] Tor found in PATH but the binary is not executable or incompatible : " << system_tor << std::endl;
    }

    // Liste des chemins locaux à vérifier
    std::vector<fs::path> candidates = {
        root_path / ("tor" EXE_EXT),
        root_path / "tor" / ("tor" EXE_EXT),
        root_path / "bin" / ("tor" EXE_EXT)
    };

    for (const auto& p : candidates) {
        if (isExecutable(p)) {
            if (testTorExecutable(p)) {
                executable_path = p;
                std::cout << "[Tor] Using local Tor: " << executable_path << std::endl;
                return true;
            }
            std::cout << "[Tor] Local Tor found but incompatible: " << p << std::endl;
        }
    }

    std::cout << "[Tor] Installation not found in " << root_path << ". Downloading..." << std::endl;
    if (!downloadAndExtract(getDownloadUrl())) {
        std::cout << "[Tor] Failed to download/extract Tor. Install Tor via your package manager." << std::endl;
        std::cout << "[Tor] On Arch Linux: sudo pacman -S tor" << std::endl;
        std::cout << "[Tor] On Debian/Ubuntu: sudo apt install tor" << std::endl;
        return false;
    }

    return true;
}

bool TorManager::downloadAndExtract(const std::string& url) {
    fs::create_directories(root_path);
    std::string archive = (root_path / "tor_archive").string();
    
#ifdef _WIN32
    std::string dl_cmd = "powershell -Command \"Invoke-WebRequest -Uri '" + url + "' -OutFile '" + archive + ".zip'\"";
    std::string ex_cmd = "powershell -Command \"Expand-Archive -Path '" + archive + ".zip' -DestinationPath '" + root_path.string() + "' -Force\"";
    if (system(dl_cmd.c_str()) != 0 || system(ex_cmd.c_str()) != 0) return false;
#else
    std::string dl_cmd = "curl -L -o " + archive + ".tar.gz " + url;
    std::string ex_cmd = "tar -xzf " + archive + ".tar.gz -C " + root_path.string() + " --strip-components=1";
    if (system(dl_cmd.c_str()) != 0 || system(ex_cmd.c_str()) != 0) return false;
#endif
    return ensureTorInstalled(); 
}

bool TorManager::createTorrc() {
    fs::create_directories(root_path / "data");
    fs::path hs_dir = root_path / "hidden_service";
    fs::create_directories(hs_dir);

#ifndef _WIN32
    fs::permissions(hs_dir, fs::perms::owner_all); // Tor needs 700 on Linux
#endif

    std::ofstream f(root_path / "torrc");
    if (!f) return false;

    f << "SocksPort " << socks_port << "\n"
      << "DataDirectory " << (root_path / "data").string() << "\n"
      << "HiddenServiceDir " << hs_dir.string() << "\n"
      << "HiddenServicePort 80 127.0.0.1:" << service_port << "\n"
      << "Log warn file " << (root_path / "tor.log").string() << "\n";
    return true;
}

long long TorManager::launchProcess(const std::vector<std::string>& args) {
#ifdef _WIN32
    std::string cmd = executable_path.string();
    for (const auto& a : args) cmd += " " + a;
    
    STARTUPINFOA si = { sizeof(si) };
    PROCESS_INFORMATION pi;
    if (!CreateProcessA(NULL, (char*)cmd.c_str(), NULL, NULL, FALSE, CREATE_NO_WINDOW, NULL, NULL, &si, &pi)) 
        return -1;
    CloseHandle(pi.hThread);
    return (long long)pi.dwProcessId;
#else
    pid_t pid = fork();
    if (pid == 0) {
        execl(executable_path.c_str(), executable_path.c_str(), "-f", args[1].c_str(), nullptr);
        exit(1);
    }
    return (long long)pid;
#endif
}

void TorManager::killProcess(long long pid) {
    if (pid <= 0) return;
#ifdef _WIN32
    HANDLE h = OpenProcess(PROCESS_TERMINATE, FALSE, (DWORD)pid);
    if (h) { TerminateProcess(h, 0); CloseHandle(h); }
#else
    kill((pid_t)pid, SIGTERM);
    waitpid((pid_t)pid, nullptr, WNOHANG);
#endif
}

bool TorManager::start() {
    if (!ensureTorInstalled()) {
        std::cerr << "[Tor] Failed to find or start Tor. Check the installation or install Tor via your package manager." << std::endl;
        return false;
    }

    if (!createTorrc()) {
        std::cerr << "[Tor] Failed to create torrc file." << std::endl;
        return false;
    }

    std::vector<std::string> args = {"-f", (root_path / "torrc").string()};
    tor_pid = launchProcess(args);
    
    if (tor_pid > 0 && waitForOnionAddress()) {
        return true;
    }

    std::cerr << "[Tor] Tor failed to start correctly or did not create a hidden service." << std::endl;
    stop();
    return false;
}

bool TorManager::waitForOnionAddress(int timeout_sec) {
    fs::path h_file = root_path / "hidden_service" / "hostname";
    for (int i = 0; i < timeout_sec; ++i) {
        if (fs::exists(h_file)) {
            std::ifstream ifs(h_file);
            if (ifs >> onion_address) return true;
        }
        std::this_thread::sleep_for(std::chrono::seconds(1));
    }
    return false;
}

void TorManager::stop() {
    killProcess(tor_pid);
    tor_pid = -1;
}

bool TorManager::isRunning() const {
    return tor_pid > 0;
}