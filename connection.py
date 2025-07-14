import socket
import threading
import json
import time
from typing import Callable, Optional
from crypto_utils import CryptoManager 
from datetime import datetime, timedelta 
from known_hosts_manager import get_nickname 
import os

class P2PConnection:
    # Constants for connection renewal
    RENEW_AFTER_MESSAGES = 9 # Renew connection after 10 messages
    RENEW_AFTER_MINUTES = 2   # Renew connection after 2 minutes

    def __init__(self, listen_port: int, message_callback: Callable[[str], None]):
        self.listen_port = listen_port
        self.message_callback = message_callback
        self.crypto = CryptoManager()
        self.connected = False
        self.socket: Optional[socket.socket] = None
        self.peer_socket: Optional[socket.socket] = None
        self._stop_flag = threading.Event()
        self._server_running = False

        # Renewal tracking variables
        self._message_count = 0
        self._last_renewal_time: Optional[datetime] = None
        self._peer_connection_details: Optional[tuple[str, int]] = None # (ip, port) of the connected peer
        self._is_server_mode = False # True if this instance is acting as a server, False if client
        self._reconnect_in_progress = threading.Event() # To prevent multiple reconnection attempts
        
        # Thread references for cleanup
        self._accept_thread: Optional[threading.Thread] = None
        self._receive_thread: Optional[threading.Thread] = None
        self._renewal_thread: Optional[threading.Thread] = None

    def start_server(self):
        """Starts the server listening for incoming connections"""
        if self._server_running:
            return  # Already running
            
        self._stop_flag.clear()  # Reset stop flag
        self._server_running = True
        
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # Allow address reuse
            self.socket.bind(('0.0.0.0', self.listen_port))
            self.socket.listen(1)
            self._is_server_mode = True # Set server mode
            
            # Start the listening thread
            self._accept_thread = threading.Thread(target=self._accept_connections, daemon=True)
            self._accept_thread.start()
            self.message_callback(f"Listening for connections on port {self.listen_port}...")
        except Exception as e:
            self.message_callback(f"Failed to start server: {str(e)}")
            self._server_running = False
            if self.socket:
                self.socket.close()
                self.socket = None

    def connect_to_peer(self, peer_ip: str, peer_port: int):
        """Connects to a remote peer with digital signature and TOFU authentication"""
        if self.connected:
            self.message_callback("Already connected to a peer")
            return False
        
        # Reset any previous connection state
        self._stop_peer_connection()
        
        # Store peer details for potential reconnection
        self._peer_connection_details = (peer_ip, peer_port)
        self._is_server_mode = False # Set client mode

        try:
            self.message_callback(f"Attempting to connect to {peer_ip}:{peer_port}...")
            self.peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.peer_socket.connect((peer_ip, peer_port))

            if not self._exchange_handshake_data(
                send_public_key_first=True, 
                peer_ip=peer_ip, 
                peer_port=peer_port
            ):
                self._close_peer_socket()
                return False

            self.connected = True
            self._initialize_renewal_trackers() # Initialize trackers on successful connection
            
            # Start threads
            self._receive_thread = threading.Thread(target=self._receive_messages, daemon=True)
            self._receive_thread.start()
            self._renewal_thread = threading.Thread(target=self._renewal_monitor, daemon=True)
            self._renewal_thread.start()
            
            return True
        except Exception as e:
            self.message_callback(f"Connection error: {str(e)}")
            self._close_peer_socket()
            return False

    def _accept_connections(self):
        """Thread for accepting incoming connections with digital signature authentication"""
        while not self._stop_flag.is_set() and self._server_running:
            try:
                if not self.socket:
                    break
                    
                self.socket.settimeout(1.0)
                client_socket, address = self.socket.accept()

                if self.connected:
                    self.message_callback(f"Rejected incoming connection from {address}: Already connected.")
                    client_socket.close()
                    continue

                # Clean up any previous connection state
                self._stop_peer_connection()

                self.peer_socket = client_socket
                # Store peer details for potential reconnection (for the server, this is the client's address)
                self._peer_connection_details = address 
                self._is_server_mode = True # Ensure server mode is set
                
                self.message_callback(f"Incoming connection from {address} received.")
                if not self._exchange_handshake_data(
                    send_public_key_first=False, 
                    peer_ip=address[0], # Pass peer_ip for TOFU check
                    peer_port=address[1] # Pass peer_port for TOFU check
                ):
                    self._close_peer_socket() # Close socket if handshake fails
                    continue

                self.connected = True
                self._initialize_renewal_trackers() # Initialize trackers on successful connection
                
                # Start threads
                self._receive_thread = threading.Thread(target=self._receive_messages, daemon=True)
                self._receive_thread.start()
                self._renewal_thread = threading.Thread(target=self._renewal_monitor, daemon=True)
                self._renewal_thread.start()
                
            except socket.timeout:
                continue
            except Exception as e:
                if not self._stop_flag.is_set() and self._server_running:
                    self.message_callback(f"Accept error: {str(e)}")
                self._close_peer_socket()

    def _exchange_handshake_data(self, send_public_key_first: bool, peer_ip: Optional[str] = None, peer_port: Optional[int] = None) -> bool:
        """
        Handles the common key exchange and authentication steps.
        `send_public_key_first`: True if this side sends its public key first (client), False if it receives first (server).
        `peer_ip` and `peer_port`: Used for TOFU verification, optional for server side where address is determined on accept.
        """
        try:
            peer_key = None
            if send_public_key_first:
                # 1. Client: Send public key, then receive peer's
                self._send_raw(self.crypto.get_public_bytes())
                peer_key = self._receive_raw()
            else:
                # 1. Server: Receive peer's public key, then send ours
                peer_key = self._receive_raw()
                self._send_raw(self.crypto.get_public_bytes())
            
            self.crypto.set_peer_public_key(peer_key)

            # TOFU: verify the peer's public key (only applicable for client, or if server gets address on accept)
            if send_public_key_first and not self._verify_tofu_identity(peer_ip, peer_port, 'client_connecting'):
                self.message_callback(f"[SECURITY] TOFU verification failed for {peer_ip}:{peer_port}. Connection refused.")
                return False
            elif not send_public_key_first and peer_ip and peer_port: # Also verify TOFU on server side if address available
                if not self._verify_tofu_identity(peer_ip, peer_port, 'server_accepting'):
                    self.message_callback(f"[SECURITY] TOFU verification failed for {peer_ip}:{peer_port}. Connection refused.")
                    return False

            # 2. Exchange of challenges
            my_challenge = os.urandom(32)
            if send_public_key_first:
                # Client: Send challenge, then receive peer's
                self._send_raw(my_challenge)
                peer_challenge = self._receive_raw()
            else:
                # Server: Receive peer's challenge, then send ours
                peer_challenge = self._receive_raw()
                self._send_raw(my_challenge)

            # 3. Exchange of signatures
            my_signature = self.crypto.sign_challenge(peer_challenge)
            if send_public_key_first:
                # Client: Send signature, then receive peer's
                self._send_raw(my_signature)
                peer_signature = self._receive_raw()
            else:
                # Server: Receive peer's signature, then send ours
                peer_signature = self._receive_raw()
                self._send_raw(my_signature)

            # 4. Verification of signature received
            if not self.crypto.verify_signature(peer_key, my_challenge, peer_signature):
                self.message_callback("[SECURITY] Invalid peer signature. Connection refused.")
                return False
            
            return True
        except Exception as e:
            self.message_callback(f"Handshake error: {str(e)}")
            return False

    def _verify_tofu_identity(self, peer_ip: str, peer_port: int, mode: str) -> bool:
        """
        Verifies the peer's public key against known_hosts for TOFU authentication.
        - If known_hosts.json doesn't exist or is invalid, it creates an empty one.
        - If host is not known (by fingerprint or IP:Port), connection is refused.
        `mode`: 'client_connecting' or 'server_accepting' to adjust verification logic.
        """
        known_hosts_path = "known_hosts.json"
        known_hosts = {"hosts": {}, "nicknames": {}} # Default empty structure
        
        try:
            with open(known_hosts_path, "r", encoding="utf-8") as f:
                loaded_data = json.load(f)
                if "hosts" in loaded_data:
                    known_hosts["hosts"] = loaded_data["hosts"]
                if "nicknames" in loaded_data:
                    known_hosts["nicknames"] = loaded_data["nicknames"]

        except (FileNotFoundError, json.JSONDecodeError):
            # If known_hosts.json doesn't exist or is invalid, create an empty one.
            try:
                with open(known_hosts_path, "w", encoding="utf-8") as f:
                    json.dump(known_hosts, f, indent=2) # Write the initial empty structure
                self.message_callback(f"[TOFU] Created empty known_hosts.json at {known_hosts_path}.")
            except IOError as e:
                self.message_callback(f"[ERROR] Could not create known_hosts.json: {e}")
                return False # Cannot even create the file, so fail

            self.message_callback(f"[SECURITY] No known hosts found. Refusing connection from {peer_ip}:{peer_port}.")
            return False # Reject because the host is not known and no previous file existed

        peer_fingerprint = self.crypto.get_peer_fingerprint()
        
        # --- NEW LOGIC for handling ephemeral ports in strict TOFU ---
        # If we are the client connecting to a server, we look for peer_ip:peer_port in known_hosts.
        # If we are the server accepting from a client, we only look for t  he peer_ip in known_hosts,
        # OR if a specific source port is known.
        
        is_known_by_ip_port = f"{peer_ip}:{peer_port}" in known_hosts["hosts"]
        is_known_by_ip_only = peer_ip in known_hosts["hosts"] # Could be if you only store IP

        # Check if the exact IP:Port is known
        if is_known_by_ip_port:
            expected_fingerprint = known_hosts["hosts"][f"{peer_ip}:{peer_port}"]
            if expected_fingerprint != peer_fingerprint:
                self.message_callback(f"[SECURITY] WARNING: The peer key for {peer_ip}:{peer_port} has changed! Connection refused.")
                return False
            else:
                self.message_callback(f"[TOFU] Known peer {peer_ip}:{peer_port} verified.")
                return True
        
        # If exact IP:Port not known, try to match by fingerprint if a known fingerprint for that IP exists
        # This handles cases where the remote port might be ephemeral on the client side.
        for stored_host_id, stored_fingerprint in known_hosts["hosts"].items():
            if ':' not in stored_host_id:
                continue
            stored_ip, _ = stored_host_id.split(':', 1) # Extract IP from stored IP:Port
            
            if stored_ip == peer_ip and stored_fingerprint == peer_fingerprint:
                # If we find the correct fingerprint for the same IP, allow it even if port differs.
                # This makes TOFU less strict about the port, but still strict on IP+fingerprint.
                self.message_callback(f"[TOFU] Known peer {peer_ip} with fingerprint matched (different port {peer_port}). Verified.")
                return True
        
        # If no matching IP:Port OR IP+Fingerprint found in known_hosts, refuse.
        self.message_callback(f"[SECURITY] UNKNOWN peer {peer_ip}:{peer_port} attempted connection. Connection refused. "
                              f"Peer fingerprint: {peer_fingerprint}. Please add it to known_hosts.json manually if desired.")
        return False # Reject unknown hosts or changed fingerprints

    def _initialize_renewal_trackers(self):
        """Initializes/resets counters and timers for connection renewal."""
        self._message_count = 0
        self._last_renewal_time = datetime.now()

    def _renewal_monitor(self):
        """Monitors connection lifetime and triggers reconnection."""
        while not self._stop_flag.is_set() and self.connected:
            should_reconnect = False

            # Check message count
            if self._message_count >= self.RENEW_AFTER_MESSAGES:
                self.message_callback(f"[SECURITY] Message limit ({self.RENEW_AFTER_MESSAGES}) reached. Initiating connection renewal.")
                should_reconnect = True

            # Check time elapsed
            if self._last_renewal_time:
                time_elapsed = datetime.now() - self._last_renewal_time
                if time_elapsed.total_seconds() >= self.RENEW_AFTER_MINUTES * 60:
                    self.message_callback(f"[SECURITY] Time limit ({self.RENEW_AFTER_MINUTES} minutes) reached. Initiating connection renewal.")
                    should_reconnect = True
            
            if should_reconnect:
                # Only trigger if a reconnection is not already in progress
                if not self._reconnect_in_progress.is_set():
                    self._reconnect_in_progress.set() # Set flag immediately
                    threading.Thread(target=self._trigger_reconnection, daemon=True).start()
                else:
                    self.message_callback("[Renewal] Reconnection already in progress. Skipping redundant trigger.")

            time.sleep(5) # Check every 5 seconds

    def _trigger_reconnection(self):
        """Stops the current connection and attempts to re-establish it."""
        self.message_callback("[RENEWAL] Initiating connection renewal: Disconnecting and reconnecting...")
        
        # Capture current peer details before stopping the connection
        current_peer_details = self._peer_connection_details
        current_is_server_mode = self._is_server_mode

        # Stop the current peer connection but keep server running if we're in server mode
        self._stop_peer_connection()
        
        # Give a moment for cleanup
        time.sleep(1) 

        # Attempt to reconnect
        if current_peer_details:
            peer_ip, peer_port = current_peer_details
            self.message_callback(f"[RENEWAL] Attempting to re-establish connection with {peer_ip}:{peer_port}...")
            
            try:
                if current_is_server_mode:
                    # If we were a server, wait for the client to reconnect
                    self.message_callback("[RENEWAL] Server mode: waiting for peer to reconnect.")
                    # Server keeps listening, client should reconnect
                else:
                    # If we were a client, try to connect to the peer again
                    success = self.connect_to_peer(peer_ip, peer_port)
                    if success:
                        self.message_callback("[RENEWAL] Connection successfully re-established.")
                    else:
                        self.message_callback("[RENEWAL] Failed to re-establish connection.")
            except Exception as e:
                self.message_callback(f"[RENEWAL] Error during re-establishment: {str(e)}")
        else:
            self.message_callback("[RENEWAL] Could not re-establish connection: No peer details found.")

        self._reconnect_in_progress.clear() # Clear flag after attempt

    def _stop_peer_connection(self):
        """Stops only the peer connection, keeping server running if applicable"""
        self.connected = False
        
        # Wait for threads to finish gracefully
        if self._receive_thread and self._receive_thread.is_alive():
            self._receive_thread.join(timeout=2.0)
        if self._renewal_thread and self._renewal_thread.is_alive():
            self._renewal_thread.join(timeout=2.0)
            
        self._close_peer_socket()
        
        # Reset thread references
        self._receive_thread = None
        self._renewal_thread = None
        
        # Clear reconnection flag if set
        self._reconnect_in_progress.clear()

    def _receive_messages(self):
        """Message reception thread"""
        peer_name = self._get_peer_nickname()
        self.message_callback(f"Connected to peer: {peer_name} ({self.crypto.get_peer_fingerprint()})")

        while not self._stop_flag.is_set() and self.connected:
            try:
                # Set a short timeout for regular message reception.
                if self.peer_socket:
                    self.peer_socket.settimeout(1.0)
                else:
                    break

                encrypted_data = self._receive_raw()
                
                decrypted = self.crypto.decrypt_message(encrypted_data)
                now = datetime.now().strftime("%H:%M:%S")
                self.message_callback(f"{peer_name} | {now}> {decrypted}")
                
                # Increment message count for received messages
                self._message_count += 1
                
            except socket.timeout:
                # Normal timeout from recv(), continue loop if no data after a short wait
                continue
            except Exception as e:
                if not self._stop_flag.is_set() and self.connected:
                    self.message_callback(f"Reception error: {str(e)}")
                break

        self.connected = False
        self._close_peer_socket()

    def _get_peer_nickname(self) -> str:
        """Attempts to retrieve the peer's nickname or returns 'Peer'."""
        try:
            peer_fingerprint = self.crypto.get_peer_fingerprint()
            nickname = get_nickname(peer_fingerprint)
            if nickname and nickname != "Peer":
                return nickname
            else:
                return "Peer"
        except Exception:
            return "Peer"

    def send_message(self, message: str):
        """Sends a message to the connected peer"""
        if not self.connected or not self.peer_socket:
            # If not connected, or if a reconnection is in progress, queue or discard message.
            # For simplicity, we'll just raise an error or log a warning.
            if self._reconnect_in_progress.is_set():
                self.message_callback("[WARNING] Message not sent: Reconnection in progress.")
                return
            raise RuntimeError("Not connected to a peer")

        try:
            encrypted = self.crypto.encrypt_message(message)
            self._send_raw(encrypted)
            
            # Increment message count for sent messages
            self._message_count += 1

        except Exception as e:
            self.message_callback(f"Sending error: {str(e)}")
            # If a send error occurs, it usually means the connection is bad.
            # Trigger a re-establishment attempt.
            if not self._reconnect_in_progress.is_set():
                self._reconnect_in_progress.set()
                threading.Thread(target=self._trigger_reconnection, daemon=True).start()

    def _send_raw(self, data: bytes):
        """Sends raw data with its size"""
        if not self.peer_socket:
            raise RuntimeError("Peer socket is not active for sending.")
        size = len(data).to_bytes(4, 'big')
        self.peer_socket.sendall(size + data)

    def _receive_raw(self) -> bytes:
        """Receives raw data with its size."""
        if not self.peer_socket:
            raise RuntimeError("Peer socket is not active for receiving.")
        try:
            size_data = self.peer_socket.recv(4)
            if not size_data:
                raise RuntimeError("Connection closed by peer")
            
            msg_size = int.from_bytes(size_data, 'big')
            data = b''
            bytes_received = 0
            while bytes_received < msg_size:
                chunk_size = min(msg_size - bytes_received, 4096)
                if chunk_size == 0:
                    break 
                chunk = self.peer_socket.recv(chunk_size) 
                if not chunk:
                    raise RuntimeError("Connection closed by peer (incomplete data)")
                data += chunk
                bytes_received += len(chunk)
            
            if bytes_received != msg_size:
                raise RuntimeError("Incomplete data received")
            
            return data
        except socket.timeout:
            raise
        except Exception as e:
            self.message_callback(f"Socket receive error: {str(e)}")
            raise

    def _close_peer_socket(self):
        """Closes the peer socket if it's open."""
        if self.peer_socket:
            try:
                self.peer_socket.shutdown(socket.SHUT_RDWR)
            except (OSError, socket.error):
                pass
            finally:
                self.peer_socket.close()
                self.peer_socket = None

    def stop(self):
        """Cleanly stops the connection"""
        self._stop_flag.set()
        self.connected = False
        self._server_running = False
        
        # Close peer socket first
        self._close_peer_socket()
        
        # Then close the listening socket
        if self.socket:
            try:
                self.socket.shutdown(socket.SHUT_RDWR)
            except (OSError, socket.error):
                pass
            finally:
                self.socket.close()
                self.socket = None

        # Wait for threads to finish (with timeout)
        for thread in [self._accept_thread, self._receive_thread, self._renewal_thread]:
            if thread and thread.is_alive():
                thread.join(timeout=2.0)