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

def add_host(address: str, fingerprint: str) -> bool:
    """
    Ajoute un hôte à known_hosts.json.
    Accepte <IP>:<PORT> ou <onion> (ou <onion>:<PORT>).
    Retourne True en cas de succès, False sinon.
    """
    if not address:
        print("Error: Address cannot be empty.")
        print("Usage: /addHost <IP_ADDRESS>:<PORT> <FINGERPRINT> ou /addHost <ONION> <FINGERPRINT>")
        return False

    is_onion = address.endswith('.onion') or ('.onion:' in address)
    if is_onion:
        # .onion seul ou .onion:port
        if ':' in address:
            onion, port = address.rsplit(':', 1)
            if not onion.endswith('.onion'):
                print("Error: Invalid .onion address format.")
                return False
            if port:
                try:
                    port_num = int(port)
                    if not (0 < port_num < 65536):
                        print("Error: Port number must be between 1 and 65535.")
                        return False
                except ValueError:
                    print("Error: Port must be a valid number.")
                    return False
        else:
            onion = address
        if not fingerprint:
            print("Error: Fingerprint cannot be empty.")
            return False
        if not (len(fingerprint) == 64 and all(c in '0123456789abcdefABCDEF' for c in fingerprint)):
            print("Error: Invalid fingerprint format. Expected a 64-character hexadecimal string (SHA256).")
            return False
        data = load_known_hosts()
        data["hosts"][address] = fingerprint
        save_known_hosts(data)
        print(f"Host {address} with fingerprint {fingerprint} added successfully.")
        return True
    # IP classique
    if ':' not in address:
        print("Error: Invalid IP:Port format. Port is missing.")
        print("Usage: /addHost <IP_ADDRESS>:<PORT> <FINGERPRINT>")
        return False
    parts = address.split(':')
    if len(parts) != 2:
        print("Error: Invalid IP:Port format. Expected format IP:Port.")
        return False
    ip_address = parts[0]
    port_str = parts[1]
    if not ip_address:
        print("Error: IP address cannot be empty.")
        return False
    try:
        port = int(port_str)
        if not (0 < port < 65536):
            print("Error: Port number must be between 1 and 65535.")
            return False
    except ValueError:
        print("Error: Port must be a valid number.")
        return False
    if not fingerprint:
        print("Error: Fingerprint cannot be empty.")
        return False
    if not (len(fingerprint) == 64 and all(c in '0123456789abcdefABCDEF' for c in fingerprint)):
        print("Error: Invalid fingerprint format. Expected a 64-character hexadecimal string (SHA256).")
        return False
    data = load_known_hosts()
    data["hosts"][address] = fingerprint
    save_known_hosts(data)
    print(f"Host {address} with fingerprint {fingerprint} added successfully.")
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
    for address, fingerprint in hosts.items():
        nickname = nicknames.get(fingerprint, "N/A")
        if address.endswith('.onion') or ('.onion:' in address):
            print(f"Onion: {address:<40}\nFingerprint: {fingerprint:<65} Nickname: {nickname}")
        else:
            if ':' in address:
                ip, port = address.split(':', 1)
                print(f"IP: {ip:<15} Port: {port:<5} \nFingerprint: {fingerprint:<65} Nickname: {nickname}")
            else:
                print(f"Address: {address:<20}\nFingerprint: {fingerprint:<65} Nickname: {nickname}")
    print("------------------")