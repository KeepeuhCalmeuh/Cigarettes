#include "torManager.hpp"
#include <iostream>
#include <fstream>
#include <thread>
#include <chrono>

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
    // List of candidate paths to check for the Tor executable
    std::vector<fs::path> candidates = {
        root_path / ("tor" EXE_EXT),
        root_path / "tor" / ("tor" EXE_EXT),
        root_path / "bin" / ("tor" EXE_EXT)
    };

    for (const auto& p : candidates) {
        if (fs::exists(p)) {
            executable_path = p;
            return true;
        }
    }

    std::cout << "[Tor] Installation non trouvée dans " << root_path << ". Téléchargement..." << std::endl;
    return downloadAndExtract(getDownloadUrl());
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
    if (!ensureTorInstalled() || !createTorrc()) return false;

    std::vector<std::string> args = {"-f", (root_path / "torrc").string()};
    tor_pid = launchProcess(args);
    
    if (tor_pid > 0 && waitForOnionAddress()) {
        return true;
    }
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