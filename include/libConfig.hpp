#ifndef LIBCONFIG_HPP
#define LIBCONFIG_HPP

#include <string>
#include <fstream>
#include <stdio.h>
#include <iostream>

using namespace std;

class Config {
public:
    Config();

    // TOR Configuration parameters
    int TOR_SERVICE_PORT;
    std::string install_dir;
    int socks_port;
    std::string version;
};

#endif // LIBCONFIG_HPP