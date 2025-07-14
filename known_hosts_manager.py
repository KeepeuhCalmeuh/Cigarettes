import json
import os

KNOWN_HOSTS_FILE = "known_hosts.json"

def load_known_hosts():
    if os.path.exists(KNOWN_HOSTS_FILE):
        with open(KNOWN_HOSTS_FILE, "r") as f:
            data = json.load(f)
            # Ensure 'hosts' and 'nicknames' keys exist, even if the file was initially empty
            if "hosts" not in data:
                data["hosts"] = {}
            if "nicknames" not in data:
                data["nicknames"] = {}
            return data
    # Return a complete initial structure if the file doesn't exist
    return {"hosts": {}, "nicknames": {}}

def save_known_hosts(data):
    with open(KNOWN_HOSTS_FILE, "w") as f:
        json.dump(data, f, indent=2)

def set_nickname(fingerprint, nickname):
    data = load_known_hosts()
    data["nicknames"][fingerprint] = nickname
    save_known_hosts(data)

def get_nickname(fingerprint):
    data = load_known_hosts()
    return data.get("nicknames", {}).get(fingerprint)

def add_host(ip_port: str, fingerprint: str) -> bool:
    """
    Adds a host to known_hosts.json.
    Validates if ip_port contains both IP address and port number.
    Returns True on success, False on failure.
    """
    if ':' not in ip_port:
        print("Error: Invalid IP:Port format. Port is missing.")
        print("Usage: /addHost <IP_ADDRESS>:<PORT> <FINGERPRINT>")
        return False
    
    parts = ip_port.split(':')
    if len(parts) != 2:
        print("Error: Invalid IP:Port format. Expected format IP:Port.")
        print("Usage: /addHost <IP_ADDRESS>:<PORT> <FINGERPRINT>")
        return False
    
    ip_address = parts[0]
    port_str = parts[1]

    if not ip_address:
        print("Error: IP address cannot be empty.")
        print("Usage: /addHost <IP_ADDRESS>:<PORT> <FINGERPRINT>")
        return False

    try:
        port = int(port_str)
        if not (0 < port < 65536): # Valid port range
            print("Error: Port number must be between 1 and 65535.")
            print("Usage: /addHost <IP_ADDRESS>:<PORT> <FINGERPRINT>")
            return False
    except ValueError:
        print("Error: Port must be a valid number.")
        print("Usage: /addHost <IP_ADDRESS>:<PORT> <FINGERPRINT>")
        return False

    if not fingerprint:
        print("Error: Fingerprint cannot be empty.")
        print("Usage: /addHost <IP_ADDRESS>:<PORT> <FINGERPRINT>")
        return False

    # Assuming fingerprints are always 64 hex characters (SHA256)
    if not (len(fingerprint) == 64 and all(c in '0123456789abcdefABCDEF' for c in fingerprint)):
        print("Error: Invalid fingerprint format. Expected a 64-character hexadecimal string (SHA256).")
        print("Usage: /addHost <IP_ADDRESS>:<PORT> <FINGERPRINT>")
        return False


    data = load_known_hosts()
    data["hosts"][ip_port] = fingerprint
    save_known_hosts(data)
    print(f"Host {ip_port} with fingerprint {fingerprint} added successfully.")
    return True

def list_known_hosts():
    data = load_known_hosts()
    hosts = data.get("hosts", {})
    nicknames = data.get("nicknames", {})

    if not hosts:
        print("No registered hosts found.")
        return

    print("Registered Hosts:")
    print("------------------")
    for ip_port, fingerprint in hosts.items():
        nickname = nicknames.get(fingerprint, "N/A")
        print(f"IP: {ip_port.split(':')[0]:<15} Port: {ip_port.split(':')[1]:<5} \nFingerprint: {fingerprint:<65} Nickname: {nickname}")
    print("------------------")