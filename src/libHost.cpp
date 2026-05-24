#include "libHost.hpp"

HostManager::HostManager() {
    ifstream hostFile("known_hosts.json");

    if (!hostFile) {
        hostData = {
            {"version", 1},
            {"hosts", json::object()}
        };
        save();
        return;
    }

    try {
        hostData = json::parse(hostFile);

        if (!hostData.contains("hosts"))
            hostData["hosts"] = json::object();

    } catch (...) {
        hostData = {
            {"version", 1},
            {"hosts", json::object()}
        };
    }
}

/* Example known_hosts.json structure:

{
  "hosts": {
    "fp_hex_or_base32": {
      "onion": "xxxxxxxxxxxxxxxx.onion",
      "nickname": "Alice",
      "first_seen": 1700000000,
      "last_seen": 1700001234,
      "trust": "unknown"
    }
  },
  "version": 1
}

*/

void HostManager::save() const {
    const char* path = "known_hosts.json";
    int fd = open(path, O_CREAT | O_WRONLY | O_TRUNC, 0600);
    if (fd < 0) {
        std::cerr << "[HostManager] Failed to open known_hosts.json for writing\n";
        return;
    }
    std::string data = hostData.dump(4);
    write(fd, data.c_str(), data.size());
    close(fd);
}
void HostManager::upsert_host(const string& fingerprint,
                              const string& onion,
                              const string& nickname)
{
    auto& hosts = hostData["hosts"];
    auto now = time(nullptr);

    if (!hosts.contains(fingerprint)) {
        hosts[fingerprint] = {
            {"onion", onion},
            {"nickname", nickname},
            {"first_seen", now},
            {"last_seen", now},
            {"trust", "unknown"}
        };
    } else {
        hosts[fingerprint]["onion"] = onion;
        hosts[fingerprint]["nickname"] = nickname;
        hosts[fingerprint]["last_seen"] = now;
    }

    save();
}

bool HostManager::get_host(const string& fingerprint, json& out) const
{
    const auto& hosts = hostData["hosts"];

    if (!hosts.contains(fingerprint))
        return false;

    out = hosts[fingerprint];
    return true;
}

void HostManager::display_host_info(const string& fingerprint)
{
    const auto& hosts = hostData["hosts"];

    if (!hosts.contains(fingerprint)) {
        cout << "Host not found\n";
        return;
    }

    const auto& host = hosts[fingerprint];

    cout << "Host Information:\n";
    cout << "Fingerprint: " << fingerprint << "\n";
    cout << "Onion Address: " << host["onion"].get<string>() << "\n";
    cout << "Nickname: " << host["nickname"].get<string>() << "\n";
    cout << "First Seen: " << host["first_seen"].get<long>() << "\n";
    cout << "Last Seen: " << host["last_seen"].get<long>() << "\n";
    cout << "Trust Level: " << host["trust"].get<string>() << "\n";
}

void HostManager::delete_host(const string& fingerprint)
{
    auto& hosts = hostData["hosts"];

    if (!hosts.contains(fingerprint)) {
        cout << "Host not found\n";
        return;
    }

    hosts.erase(fingerprint);
    save();
}

void HostManager::list_hosts()
{
    const auto& hosts = hostData["hosts"];

    if (hosts.empty()) {
        cout << "No known hosts found.\n";
        return;
    }

    cout << "================================================================================\n";
    printf("%-32s | %-56s | %-15s\n", "Fingerprint (Prefix)", "Onion Address", "Nickname");
    cout << "--------------------------------------------------------------------------------\n";

    for (auto it = hosts.begin(); it != hosts.end(); ++it) {
        string fp = it.key();
        string display_fp = fp.substr(0, 32) + "..."; // Show prefix
        string onion = it.value()["onion"].get<string>();
        string nickname = it.value()["nickname"].get<string>();

        printf("%-32s | %-56s | %-15s\n", display_fp.c_str(), onion.c_str(), nickname.c_str());
    }
    cout << "================================================================================\n";
}

string HostManager::get_onion(const string& fingerprint) const
{
    const auto& hosts = hostData["hosts"];

    if (!hosts.contains(fingerprint))
        return "";

    return hosts[fingerprint]["onion"].get<string>();
}

string HostManager::get_nickname(const string& fingerprint) const
{
    const auto& hosts = hostData["hosts"];

    if (!hosts.contains(fingerprint))
        return "";

    return hosts[fingerprint]["nickname"].get<string>();
}