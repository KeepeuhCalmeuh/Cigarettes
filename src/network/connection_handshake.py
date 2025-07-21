# Handshake et authentification pour P2PConnection
from datetime import datetime
import json
import os
from colorama import Fore, Style

class HandshakeMixin:
    def _exchange_handshake_data(self, send_public_key_first: bool, peer_ip: str = None, peer_port: int = None) -> bool:
        try:
            challenge = os.urandom(32)
            if send_public_key_first:
                handshake_data = {
                    "public_key": self.crypto.get_public_bytes().hex(),
                    "challenge": challenge.hex()
                }
                self._send_raw(json.dumps(handshake_data).encode())
                response_data = json.loads(self._receive_raw().decode())
                peer_public_key_bytes = bytes.fromhex(response_data["public_key"])
                peer_challenge = bytes.fromhex(response_data["challenge"])
                peer_signature = bytes.fromhex(response_data["signature"])
                if not self.crypto.verify_signature(peer_public_key_bytes, challenge, peer_signature):
                    self.message_callback("Peer authentication failed: Invalid signature")
                    return False
                self.crypto.set_peer_public_key(peer_public_key_bytes)
                my_signature = self.crypto.sign_challenge(peer_challenge)
                signature_data = {"signature": my_signature.hex()}
                self._send_raw(json.dumps(signature_data).encode())
            else:
                handshake_data = json.loads(self._receive_raw().decode())
                peer_public_key_bytes = bytes.fromhex(handshake_data["public_key"])
                peer_challenge = bytes.fromhex(handshake_data["challenge"])
                self.crypto.set_peer_public_key(peer_public_key_bytes)
                my_signature = self.crypto.sign_challenge(peer_challenge)
                response_data = {
                    "public_key": self.crypto.get_public_bytes().hex(),
                    "challenge": challenge.hex(),
                    "signature": my_signature.hex()
                }
                self._send_raw(json.dumps(response_data).encode())
                signature_data = json.loads(self._receive_raw().decode())
                peer_signature = bytes.fromhex(signature_data["signature"])
                if not self.crypto.verify_signature(peer_public_key_bytes, challenge, peer_signature):
                    self.message_callback("Peer authentication failed: Invalid signature")
                    return False
            if peer_ip and peer_port:
                if not self._verify_tofu_identity(peer_ip, peer_port, "client" if send_public_key_first else "server"):
                    return False
            self.message_callback(Fore.LIGHTGREEN_EX + f"[{self._get_peer_nickname()}  |  {datetime.now().strftime('%H:%M:%S')}] Secure connection established" + Style.RESET_ALL)
            return True
        except Exception as e:
            self.message_callback(f"Handshake failed: {str(e)}")
            return False

    def _verify_tofu_identity(self, peer_ip: str, peer_port: int, mode: str) -> bool:
        try:
            peer_fingerprint = self.crypto.get_peer_fingerprint()
            expected_fingerprint = self.hosts_manager.get_host_fingerprint(f"{peer_ip}:{peer_port}")
            if expected_fingerprint:
                if expected_fingerprint != peer_fingerprint:
                    self.message_callback(f"WARNING: Peer fingerprint mismatch!")
                    self.message_callback(f"Expected: {expected_fingerprint}")
                    self.message_callback(f"Received: {peer_fingerprint}")
                    return False
                else:
                    self.message_callback(f"Peer identity verified (TOFU)")
            else:
                self.message_callback(f"New peer: {peer_fingerprint}")
                self.message_callback(f"Add to known hosts with: /addHost {peer_ip}:{peer_port} {peer_fingerprint}")
            return True
        except Exception as e:
            self.message_callback(f"TOFU verification failed: {str(e)}")
            return False

    def _initialize_renewal_trackers(self) -> None:
        self._message_count = 0
        self._last_renewal_time = datetime.now()

    def _renewal_monitor(self) -> None:
        while self.connected and not self._stop_flag.is_set():
            import time
            time.sleep(60)
            if self._should_renew_connection():
                self._trigger_reconnection()

    def _should_renew_connection(self) -> bool:
        if not self._last_renewal_time:
            return False
        time_elapsed = (datetime.now() - self._last_renewal_time).total_seconds() / 60
        return (self._message_count >= self.RENEW_AFTER_MESSAGES or 
                time_elapsed >= self.RENEW_AFTER_MINUTES)

    def _trigger_reconnection(self) -> None:
        if self._reconnect_in_progress.is_set():
            return
        self._reconnect_in_progress.set()
        self.message_callback("Renewing connection...")
        try:
            old_peer_details = self._peer_connection_details
            old_is_server = self._is_server_mode
            self._stop_peer_connection()
            if old_is_server:
                import time
                time.sleep(2)
            else:
                if old_peer_details:
                    peer_ip, peer_port = old_peer_details
                    if self._is_onion_address(peer_ip):
                        self.connect_to_onion_peer(peer_ip, self.crypto.get_peer_fingerprint(), peer_port)
                    else:
                        self.connect_to_peer(peer_ip, peer_port)
        finally:
            self._reconnect_in_progress.clear()

    def _is_onion_address(self, address: str) -> bool:
        return address.endswith('.onion') 