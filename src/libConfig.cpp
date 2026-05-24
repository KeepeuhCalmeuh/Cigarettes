#include "libConfig.hpp"
#include <sstream>
#include <fstream>
#include <iostream>
#include <stdexcept>

Config::Config() {
    std::ifstream file(".config");
    if (file.is_open()) {
        std::string line;
        bool in_tor_config_section = false;

        while (std::getline(file, line)) {
            // Trim whitespace
            line.erase(0, line.find_first_not_of(" \t"));
            line.erase(line.find_last_not_of(" \t") + 1);

            // Skip empty lines or comments
            if (line.empty() || line[0] == '#') {
                continue;
            }

            // Check for section headers
            if (line[0] == '[' && line.back() == ']') {
                std::string section = line.substr(1, line.size() - 2);
                in_tor_config_section = (section == "tor-config");
                continue;
            }

            // Only parse lines in the [tor-config] section
            if (!in_tor_config_section) {
                continue;
            }

            // Parse key-value pairs
            size_t delimiter_pos = line.find(' ');
            if (delimiter_pos != std::string::npos) {
                std::string key = line.substr(0, delimiter_pos);
                std::string value = line.substr(delimiter_pos + 1);

                // Remove quotes around values if present
                if (!value.empty() && value.front() == '"' && value.back() == '"') {
                    value = value.substr(1, value.size() - 2);
                }

                // Assign values to configuration variables
                try {
                    if (key == "TOR_SERVICE_PORT") {
                        TOR_SERVICE_PORT = std::stoi(value);
                    } else if (key == "install_dir") {
                        install_dir = value;
                    } else if (key == "socks_port") {
                        socks_port = std::stoi(value);
                    } else if (key == "version") {
                        version = value;
                    }
                } catch (const std::exception &e) {
                    std::cerr << "Error parsing value for key: " << key << " - " << e.what() << std::endl;
                }
            }
        }

        file.close();
    } else {
        // Set default configuration values if file cannot be opened
        TOR_SERVICE_PORT = 9050;
        install_dir = "tor";
        socks_port = 9050;
        version = "14.5.4";

        std::cerr << "Warning: Could not open .config file. Using default configuration." << std::endl;
    }
}