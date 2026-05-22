# Cigarettes 

**Cigarettes** is a lightweight, secure, and anonymous P2P messenger built with C++. It leverages the Tor Network to provide anonymity and OpenSSL for robust End-to-End Encryption (E2EE), ensuring your conversations remain private and untraceable.

For now, only on linux.

## Key Features

-   **Anonymity via Tor**: Communicates exclusively through Tor Hidden Services (`.onion` addresses). No IP addresses are ever exposed.
-   **End-to-End Encryption**: Secure handshake and session management using RSA-4096 and AES-256-GCM. Your messages are encrypted before they leave your device.
-   **Peer-to-Peer**: No central server. 
-   **Host Management**: Keep track of your contacts with a local `known_hosts.json` file. Support for nicknames and fingerprint verification.
-   **Automatic Tor Management**: The application can automatically download, configure, and launch the Tor binary if not found.
-   **Interactive CLI**: Simple and intuitive command-line interface.

## Security Model

1.  **Transport**: All traffic is routed through the Tor network, providing metadata protection and location anonymity.
2.  **Authentication**: Peers are identified by their unique cryptographic fingerprints (derived from their public keys).
3.  **Confidentiality**: A challenge-response handshake establishes a shared AES-256-GCM key for each session, ensuring that only the intended recipient can read your messages.

## Prerequisites

To build and run **Cigarettes**, you need:

-   A C++17 compatible compiler (e.g., `g++`).
-   **OpenSSL** development libraries (`libssl-dev` on Debian/Ubuntu).
-   `pthread` support.
-   `nlohmann-json` (Automaticaly fetch during the compilation).

## Getting Started

### Installation & Build

Clone the repository and compile the project using CMake:

```bash
mkdir build
cd build
cmake ..
make
```
This will compile both the `Cigarettes` executable and the `libCigarettes.so` shared library in the `build/` directory. For now, the libCigarettes.so is not usable.

### Launching the Messenger

Run the binary from the `build` directory:
If no argument (service port, installation directory (for Tor), and SOCKS5 port) is provided, the `.config` file will be used. If the `.config` file does not exist, the default values will be used.

```bash
./Cigarettes
or
./Cigarettes 8080 tor_data 9050
```

-   **8080**: The port where your hidden service will listen.
-   **tor_data**: The directory where Tor configuration and keys will be stored.
-   **9050**: The SOCKS5 proxy port used to route outgoing traffic through Tor.

If nothing is provided at the start of the program, it will try to use the data in  the .config file if provided in the same directory as the executable (an exemple is in the repo.). If nothing is found, it will use the classic ones : 8080 tor 9050.

## Command Guide

Once launched, you can use the following commands:

| Command | Description |
| :--- | :--- |
| `/connect <addr.onion>` | Initiate a secure connection to a peer. |
| `/disconnect` | Close the current active connection. |
| `/addHost <addr.onion> <fingerprint> <nickname>` | Add a peer to your known hosts list. |
| `/listHosts` | List all saved peers and their fingerprints. |
| `/removeHost <fingerprint>` | Remove a peer from your known hosts. |
| `/rename <fingerprint> <new_nickname>` | Rename a peer in your list. |
| `/ping` | Send a ping to the current peer and display the RTT. |
| `/filetransfer <path>` | Send a file to the current peer. |
| `/help` | Display the help menu. |
| `/exit` | Safely shutdown the application and Tor. |

To reset your identity, you can just delete the `private_key.pem` file in the `keys` directory and restart the application. Same goes for the `tor_data` directory.

## Library
[See LIBRARY_DOC.md](LIBRARY_DOC.md).
Not usable for now.

## Acknowledgements

This project uses [JSON for Modern C++](https://github.com/nlohmann/json) by Niels Lohmann, automatically fetched during the CMake build process.

---
*Stay anonymous. Stay secure.* 🚬
