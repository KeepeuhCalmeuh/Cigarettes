# Cigarettes - Encrypted P2P Messaging

A command-line encrypted P2P messaging application using modern cryptographic technologies.

## Features

- Direct P2P (peer-to-peer) communication
- End-to-end encryption with ECC (Elliptic Curve Cryptography)
- Diffie-Hellman key exchange on an elliptic curve
- Message encryption with AES-256-GCM
- Identity verification using public key fingerprints
- Simple command-line interface

## Prerequisites

- Python 3.8+
- Cryptography package

## Installation

1. Create a virtual environment (recommended):

```bash
python -m venv venv
source venv/bin/activate # Linux/MacOS
# or
.\venv\Scripts\activate # Windows
```

2. Install the dependencies:

```bash
pip install cryptography
```

## Usage

1. Start the application by specifying a listening port :

```bash
python main.py 5000
```

2. The application will display your public key fingerprint and listen for connections.

3. Add people to you known_hosts.json file.

```
/addHost <PEER_IP_ADDRESS>:<PEER_PORT> <PEER_FINGERPRINT>
```

For example : `/addhost 192.198.1.2:5000 a2ae88fb900e1769e94850616cd7c9542d06ba3e2517bb47fbd9ab98debb6470`

4. To connect to a peer, use the command:

```bash
/connect <ip> <port>
```

For example: `/connect 192.168.1.2 5000`

5. Type your messages and press Enter to send them.

### Available Commands

- `/connect <ip> <port>`: Connects to a remote peer
- `/status`: Display connexion informations.
- `/stop`: Disconnects the connection with the peer without exiting the application
- `/save`: Saves the chat history to a text file (`history` folder)
- `/ping`: Display the ping between you and your peer.
- `/fingerprint`: Displays your public key fingerprint
- `/rename <fingerprint> <new_name>`: Rename a peer in known hosts
- `/addHost <ip:port> <fingerprint>`: Add a host to known hosts
- `/listHosts`: List all known hosts
- `/multiline`: Toggle multi-line message mode (use Shift+Enter for new line, Enter to send)
- `/help`: Displays command help
- `/exit`: Exits the application

## Security

- All messages are encrypted with AES-256-GCM
- Session keys are derived via ECDH and HKDF
- Identity verification via SHA-256 public key fingerprints
- Connection is automatically renewed (cut and re-established) after a certain number of messages (currently 10 messages) or a specific time interval (currently 2 minutes) to ensure fresh session keys. This enhances forward secrecy.

## Known Limitations / TODOs

- Sometimes, when the connection fail, you need to exit with /exit and restart the program to avoid timeout. This will be corrected in future versions.

## Note

This application is designed for educational demonstrations. For production use, additional security features would be required.
