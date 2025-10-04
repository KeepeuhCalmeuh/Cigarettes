# Cigarettes - Encrypted P2P Messaging

A command-line encrypted P2P messaging application using modern cryptographic technologies.

## Features

- Direct P2P (peer-to-peer) communication
- End-to-end encryption with ECC (Elliptic Curve Cryptography)
- Diffie-Hellman key exchange on an elliptic curve
- Message encryption with AES-256-GCM
- Identity verification using public key fingerprints
- SMSoIP over the Tor Network
- Simple command-line interface

## Prerequisites

- Python 3.8+
- Cryptography, Socks, Colorama, Requests packages

## Installation

1. Create a virtual environment (recommended):

```bash
python -m venv venv
source venv/bin/activate # Linux/MacOS
```
or
```bash
.\venv\Scripts\activate # Windows
```

2. Install the dependencies:

```bash
pip install -r requirements.txt
```
## Usage

**Please note that Tor currently does not support ARM machines and therefore Cigarettes is not deployable**

1. Start the application :

```bash
python main.py
```

2. The application will display your public key fingerprint, your .onion adress and listen for connections.

3. Add people to you known_hosts.json file, and let people add you to their known_hosts.json file.

```
/addHost <peer_onion_adress> <PEER_FINGERPRINT>
```

For example : `/addhost yq5jjvr7drkjrelzhut7kgclfuro65jjlivyzfmxiq2kyv5lickrl4qd.onion a2ae88fb900e1769e94850616cd7c9542d06ba3e2517bb47fbd9ab98debb6470`

4. To connect to a peer, use the command:

```bash
/connect <peer_onion_adress> <PEER_FINGERPRINT> <peer_listening_port (optional, default : 34567)>
```

For example: `/connect yq5jjvr7drkjrelzhut7kgclfuro65jjlivyzfmxiq2kyv5lickrl4qd.onion a2ae88fb900e1769e94850616cd7c9542d06ba3e2517bb47fbd9ab98debb6470`

5. Type your messages and press Enter to send them. 

### Available Commands

- `/connect <peer_onion_adress> <PEER_FINGERPRINT> <peer_listening_port (optional, default : 34567)>`: Connects to a remote peer
- `/status`: Display connexion informations.
- `/stop`: Disconnects the connection with the peer without exiting the application
- `/save`: Saves the chat history to a text file (`history` folder)
- `/send_file <file_path>`: Send a file to the connected peer
- `/ping`: Display the ping between you and your peer.
- `/fingerprint`: Displays your public key fingerprint
- `/rename <fingerprint> <new_name>`: Rename a peer in known hosts
- `/addHost (or /ad) <peer_onion_adress> <fingerprint>`: Add a host to known hosts
- `/removehost (or /rmh) <peer_onion_address>`: Remove a peer from the host list.
- `/listHosts (or /lh)`: List all known hosts
- `/multiline`: Toggle multi-line message mode (use Shift+Enter for new line, Enter to send)
- `/help`: Displays command help
- `/exit`: Exits the application

## Security

- All messages are encrypted with AES-256-GCM
- Session keys are derived via ECDH and HKDF
- Identity verification via SHA-256 public key fingerprints


## Known Limitations / TODOs
- ARM systems support


## Note

This application is designed for educational demonstrations. For production use, additional security features would be required.
