"""
Known hosts management for storing and retrieving peer information.
Handles host addresses, fingerprints, and nicknames.
"""

import json
import os
from typing import Dict, Optional, List


class KnownHostsManager:
    """
    Manages known hosts, their fingerprints, and nicknames.
    Provides methods for adding, removing, and querying host information.
    """
    
    def __init__(self, hosts_file: str = None):
        """
        Initialize the hosts manager.
        
        Args:
            hosts_file: Path to the JSON file storing host information
        """
        # Par défaut, on place known_hosts.json dans le dossier keys/
        if hosts_file is None:
            keys_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'keys')
            os.makedirs(keys_dir, exist_ok=True)
            hosts_file = os.path.join(keys_dir, "known_hosts.json")
            # Migration automatique si l'ancien fichier existe à la racine
            old_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "known_hosts.json")
            if os.path.exists(old_path) and not os.path.exists(hosts_file):
                try:
                    os.rename(old_path, hosts_file)
                    print(f"[LOG] known_hosts.json migrated to {hosts_file}")
                except Exception as e:
                    print(f"[LOG] Could not migrate known_hosts.json: {e}")
        self.hosts_file = hosts_file
        self._data = self._load_data()

    def _load_data(self) -> Dict:
        """Load host data from file or create default structure."""
        if os.path.exists(self.hosts_file):
            with open(self.hosts_file, "r") as f:
                data = json.load(f)
                # Ensure required keys exist
                if "hosts" not in data:
                    data["hosts"] = {}
                if "nicknames" not in data:
                    data["nicknames"] = {}
                return data
        return {"hosts": {}, "nicknames": {}}

    def _save_data(self) -> None:
        """Save host data to file."""
        with open(self.hosts_file, "w") as f:
            json.dump(self._data, f, indent=2)

    def set_nickname(self, fingerprint: str, nickname: str) -> None:
        """
        Set a nickname for a fingerprint.
        
        Args:
            fingerprint: The peer's fingerprint
            nickname: The nickname to assign
        """
        self._data["nicknames"][fingerprint] = nickname
        self._save_data()

    def get_nickname(self, fingerprint: str) -> Optional[str]:
        """
        Get the nickname for a fingerprint.
        
        Args:
            fingerprint: The peer's fingerprint
            
        Returns:
            The nickname if found, None otherwise
        """
        return self._data.get("nicknames", {}).get(fingerprint)

    def add_host(self, address: str, fingerprint: str) -> bool:
        """
        Add a host to known hosts.
        
        Args:
            address: Host address (IP:port or onion address)
            fingerprint: The peer's fingerprint
            
        Returns:
            True if successful, False otherwise
        """
        if not address:
            print("Error: Address cannot be empty.")
            return False

        if not fingerprint:
            print("Error: Fingerprint cannot be empty.")
            return False

        if not self._validate_fingerprint(fingerprint):
            print("Error: Invalid fingerprint format. Expected a 64-character hexadecimal string (SHA256).")
            return False

        # Validate address format
        if not self._validate_address(address):
            return False

        self._data["hosts"][address] = fingerprint
        self._save_data()
        print(f"Host {address} with fingerprint {fingerprint} added successfully.")
        return True

    def remove_host(self, address: str) -> bool:
        """
        Remove a host from known hosts.
        
        Args:
            address: The host address to remove
            
        Returns:
            True if removed, False if not found
        """
        if address in self._data["hosts"]:
            del self._data["hosts"][address]
            self._save_data()
            print(f"Host {address} removed successfully.")
            return True
        else:
            print(f"Host {address} not found in known hosts.")
            return False

    def list_known_hosts(self) -> None:
        """Display all known hosts with their information."""
        hosts = self._data.get("hosts", {})
        nicknames = self._data.get("nicknames", {})
        
        if not hosts:
            print("No registered hosts found.")
            return
            
        print("Registered Hosts:")
        print("------------------")
        for address, fingerprint in hosts.items():
            nickname = nicknames.get(fingerprint, "N/A")
            if self._is_onion_address(address):
                print(f"Onion: {address:<40}")
                print(f"Fingerprint: {fingerprint:<65} Nickname: {nickname}\n")
            else:
                if ':' in address:
                    ip, port = address.split(':', 1)
                    print(f"IP: {ip:<15} Port: {port:<5}")
                    print(f"Fingerprint: {fingerprint:<65} Nickname: {nickname}\n")
                else:
                    print(f"Address: {address:<20}")
                    print(f"Fingerprint: {fingerprint:<65} Nickname: {nickname}\n")
        print("------------------")

    def get_host_fingerprint(self, address: str) -> Optional[str]:
        """
        Get the fingerprint for a host address.
        
        Args:
            address: The host address
            
        Returns:
            The fingerprint if found, None otherwise
        """
        return self._data.get("hosts", {}).get(address)

    def get_all_fingerprints(self) -> List[str]:
        """Get all fingerprints from known hosts."""
        return list(self._data.get("hosts", {}).values())

    def _validate_fingerprint(self, fingerprint: str) -> bool:
        """Validate fingerprint format."""
        return (len(fingerprint) == 64 and 
                all(c in '0123456789abcdefABCDEF' for c in fingerprint))

    def _validate_address(self, address: str) -> bool:
        """Validate address format."""
        if self._is_onion_address(address):
            return self._validate_onion_address(address)
        else:
            return self._validate_ip_address(address)

    def _is_onion_address(self, address: str) -> bool:
        """Check if address is an onion address."""
        return address.endswith('.onion') or ('.onion:' in address)

    def _validate_onion_address(self, address: str) -> bool:
        """Validate onion address format."""
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
        return True

    def _validate_ip_address(self, address: str) -> bool:
        """Validate IP address format."""
        if ':' not in address:
            print("Error: Invalid IP:Port format. Port is missing.")
            print("Usage: <IP_ADDRESS>:<PORT>")
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
            
        return True 

    def get_fingerprint_by_nickname(self, nickname: str) -> Optional[str]:
        """
        Get the fingerprint associated with a nickname.
        
        Args:
            nickname: The nickname to look up
            
        Returns:
            The fingerprint if found, None otherwise
        """
        for fp, nick in self._data.get("nicknames", {}).items():
            if nick == nickname:
                return fp
        return None
    
    def get_onion_by_fingerprint(self, fingerprint: str) -> Optional[str]:
        """
        Get the onion address associated with a fingerprint.
        
        Args:
            fingerprint: The fingerprint to look up
            
        Returns:
            The onion address if found, None otherwise
        """
        for address, fp in self._data.get("hosts", {}).items():
            if fp == fingerprint and self._is_onion_address(address):
                return address
        return None