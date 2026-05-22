#ifndef LIBHOST_HPP
#define LIBHOST_HPP

#include <stdio.h>
#include <iostream>
#include <fstream>
#include <ctime>
#include <sys/stat.h>
#include <nlohmann/json.hpp>

#ifndef _WIN32
#include <fcntl.h>
#include <unistd.h>
#endif

using namespace std;
using json = nlohmann::json;

class HostManager {
public:
    HostManager();

    void upsert_host(const string& fingerprint, const string& onion, const string& nickname);
    bool get_host(const string& fingerprint, json& out) const;
    void display_host_info(const string& fingerprint);
    void list_hosts();
    void delete_host(const string& fingerprint);
    string get_onion(const string& fingerprint) const;
    string get_nickname(const string& fingerprint) const;
private:
    json hostData;
    void save() const;
};

#endif // LIBHOST_HPP