"""
P2P connection management for secure peer-to-peer communication.
Handles connection establishment, message exchange, and file transfers.
"""

import socket
import threading
import json
import time
from typing import Callable, Optional, Tuple
from datetime import datetime
import ipaddress
import os
from colorama import Fore, Style
import socks

from ..core.crypto import CryptoManager
from ..core.hosts import KnownHostsManager


class P2PConnection:
    """
    Manages P2P connections with encryption, authentication, and file transfer capabilities.
    """
    
    # Constants for connection renewal
    RENEW_AFTER_MESSAGES = 10000  # Renew connection after 10000 messages
    RENEW_AFTER_MINUTES = 60      # Renew connection after 60 minutes

    def __init__(self, listen_port: int, message_callback: Callable[[str], None]):
        """
        Initialize the P2P connection manager.
        
        Args:
            listen_port: Port to listen for incoming connections
            message_callback: Callback function for received messages
        """
        self.listen_port = listen_port
        self.message_callback = message_callback
        self.crypto = CryptoManager()
        self.hosts_manager = KnownHostsManager()
        
        # Connection state
        self.connected = False
        self.socket: Optional[socket.socket] = None
        self.peer_socket: Optional[socket.socket] = None
        self._stop_flag = threading.Event()
        self._server_running = False

        # Renewal tracking
        self._message_count = 0
        self._last_renewal_time: Optional[datetime] = None
        self._peer_connection_details: Optional[Tuple[str, int]] = None
        self._is_server_mode = False
        self._reconnect_in_progress = threading.Event()
        
        # Thread management
        self._accept_thread: Optional[threading.Thread] = None
        self._receive_thread: Optional[threading.Thread] = None
        self._renewal_thread: Optional[threading.Thread] = None

        # Ping functionality
        self._ping_responses = {}
        self._ping_lock = threading.Lock()
        self._pending_file_path = None

    def start_server(self) -> None:
        """Start the server listening for incoming connections (idempotent)."""
        if self._server_running:
            print(f"[LOG] P2P server already running on port {self.listen_port}")
            return
        self._stop_flag.clear()
        self._server_running = True
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind(('0.0.0.0', self.listen_port))
            self.socket.listen(1)
            self._is_server_mode = True
            print(f"[LOG] P2P server started and listening on port {self.listen_port}")
            self._accept_thread = threading.Thread(target=self._accept_connections, daemon=True)
            self._accept_thread.start()
        except Exception as e:
            self.message_callback(f"Failed to start server: {str(e)}")
            self._server_running = False
            if self.socket:
                self.socket.close()
                self.socket = None

    def connect_to_peer(self, peer_ip: str, peer_port: int, timeout: int = 10) -> bool:
        """
        Connect to a remote peer with authentication.
        
        Args:
            peer_ip: IP address of the peer
            peer_port: Port of the peer
            timeout: Connection timeout in seconds
            
        Returns:
            True if connection successful, False otherwise
        """
        if self.connected:
            self.message_callback("Already connected to a peer")
            return False
        
        if not self._validate_ip_address(peer_ip):
            self.message_callback(f"Invalid IP address: {peer_ip}")
            return False
        
        if self._is_private_ip(peer_ip):
            self.message_callback(Fore.LIGHTYELLOW_EX + f"[INFO] Connecting to private IP: {peer_ip}" + Style.RESET_ALL)
        else:
            self.message_callback(Fore.LIGHTYELLOW_EX + f"[INFO] Connecting to public IP: {peer_ip}" + Style.RESET_ALL)

        self._stop_peer_connection()
        self._peer_connection_details = (peer_ip, peer_port)
        self._is_server_mode = False

        try:
            self.message_callback(f"Attempting to connect to {peer_ip}:{peer_port}...")
            self.peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.peer_socket.settimeout(timeout)
            self.peer_socket.connect((peer_ip, peer_port))
            self.peer_socket.settimeout(None)

            if not self._exchange_handshake_data(
                send_public_key_first=True,
                peer_ip=peer_ip,
                peer_port=peer_port
            ):
                self._close_peer_socket()
                return False

            self.connected = True
            self._initialize_renewal_trackers()
            
            self._receive_thread = threading.Thread(target=self._receive_messages, daemon=True)
            self._receive_thread.start()
            self._renewal_thread = threading.Thread(target=self._renewal_monitor, daemon=True)
            self._renewal_thread.start()
            
            return True
        except Exception as e:
            self.message_callback(f"Connection error: {str(e)}")
            self._close_peer_socket()
            return False

    def connect_to_onion_peer(self, onion_address: str, fingerprint: str, port: int = 34567, timeout: int = 10) -> bool:
        """
        Connect to a peer via Tor onion address.
        
        Args:
            onion_address: Onion address of the peer
            fingerprint: Expected fingerprint of the peer
            port: Port number
            timeout: Connection timeout in seconds
            
        Returns:
            True if connection successful, False otherwise
        """
        if self.connected:
            self.message_callback("Already connected to a peer")
            return False

        self._stop_peer_connection()
        self._peer_connection_details = (onion_address, port)
        self._is_server_mode = False

        try:
            self.message_callback(f"Attempting to connect to {onion_address}:{port} via Tor...")
            self.peer_socket = socks.socksocket()
            self.peer_socket.set_proxy(socks.SOCKS5, "127.0.0.1", 9050)
            self.peer_socket.settimeout(timeout)
            self.peer_socket.connect((onion_address, port))
            self.peer_socket.settimeout(None)

            if not self._exchange_handshake_data(
                send_public_key_first=True,
                peer_ip=onion_address,
                peer_port=port
            ):
                self._close_peer_socket()
                return False

            self.connected = True
            self._initialize_renewal_trackers()
            self._receive_thread = threading.Thread(target=self._receive_messages, daemon=True)
            self._receive_thread.start()
            self._renewal_thread = threading.Thread(target=self._renewal_monitor, daemon=True)
            self._renewal_thread.start()
            return True
        except Exception as e:
            self.message_callback(f"Connection error: {str(e)}")
            self._close_peer_socket()
            return False

    def _accept_connections(self) -> None:
        """Thread for accepting incoming connections with authentication."""
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

                self._stop_peer_connection()
                self.peer_socket = client_socket
                self._peer_connection_details = address
                self._is_server_mode = True
                
                self.message_callback(f"Incoming connection from {address} received.")
                if not self._exchange_handshake_data(
                    send_public_key_first=False,
                    peer_ip=address[0],
                    peer_port=address[1]
                ):
                    self._close_peer_socket()
                    continue

                self.connected = True
                self._initialize_renewal_trackers()
                
                self._receive_thread = threading.Thread(target=self._receive_messages, daemon=True)
                self._receive_thread.start()
                self._renewal_thread = threading.Thread(target=self._renewal_monitor, daemon=True)
                self._renewal_thread.start()
                
                self.message_callback(f"Successfully connected to {address}")
                
            except socket.timeout:
                continue
            except Exception as e:
                if not self._stop_flag.is_set():
                    self.message_callback(f"Error accepting connection: {str(e)}")

    def _exchange_handshake_data(self, send_public_key_first: bool, peer_ip: Optional[str] = None, peer_port: Optional[int] = None) -> bool:
        """
        Exchange handshake data and establish encrypted session.
        
        Args:
            send_public_key_first: Whether this peer sends its public key first
            peer_ip: IP address of the peer
            peer_port: Port of the peer
            
        Returns:
            True if handshake successful, False otherwise
        """
        try:
            # Generate challenge for authentication
            challenge = os.urandom(32)
            
            if send_public_key_first:
                # Send public key and challenge
                handshake_data = {
                    "public_key": self.crypto.get_public_bytes().hex(),
                    "challenge": challenge.hex()
                }
                self._send_raw(json.dumps(handshake_data).encode())
                
                # Receive peer's public key and challenge
                response_data = json.loads(self._receive_raw().decode())
                peer_public_key_bytes = bytes.fromhex(response_data["public_key"])
                peer_challenge = bytes.fromhex(response_data["challenge"])
                peer_signature = bytes.fromhex(response_data["signature"])
                
                # Verify peer's signature
                if not self.crypto.verify_signature(peer_public_key_bytes, challenge, peer_signature):
                    self.message_callback("Peer authentication failed: Invalid signature")
                    return False
                
                # Set peer's public key and derive session key
                self.crypto.set_peer_public_key(peer_public_key_bytes)
                
                # Sign peer's challenge and send
                my_signature = self.crypto.sign_challenge(peer_challenge)
                signature_data = {"signature": my_signature.hex()}
                self._send_raw(json.dumps(signature_data).encode())
                
            else:
                # Receive peer's public key and challenge
                handshake_data = json.loads(self._receive_raw().decode())
                peer_public_key_bytes = bytes.fromhex(handshake_data["public_key"])
                peer_challenge = bytes.fromhex(handshake_data["challenge"])
                
                # Set peer's public key and derive session key
                self.crypto.set_peer_public_key(peer_public_key_bytes)
                
                # Sign peer's challenge and send response
                my_signature = self.crypto.sign_challenge(peer_challenge)
                response_data = {
                    "public_key": self.crypto.get_public_bytes().hex(),
                    "challenge": challenge.hex(),
                    "signature": my_signature.hex()
                }
                self._send_raw(json.dumps(response_data).encode())
                
                # Receive peer's signature
                signature_data = json.loads(self._receive_raw().decode())
                peer_signature = bytes.fromhex(signature_data["signature"])
                
                # Verify peer's signature
                if not self.crypto.verify_signature(peer_public_key_bytes, challenge, peer_signature):
                    self.message_callback("Peer authentication failed: Invalid signature")
                    return False
            
            # TOFU (Trust On First Use) verification
            if peer_ip and peer_port:
                if not self._verify_tofu_identity(peer_ip, peer_port, "client" if send_public_key_first else "server"):
                    return False
            
            self.message_callback(Fore.LIGHTGREEN_EX + f"[{self._get_peer_nickname()}  |  {datetime.now().strftime('%H:%M:%S')}] Secure connection established" + Style.RESET_ALL)
            return True
            
        except Exception as e:
            self.message_callback(f"Handshake failed: {str(e)}")
            return False

    def _verify_tofu_identity(self, peer_ip: str, peer_port: int, mode: str) -> bool:
        """
        Verify peer identity using Trust On First Use (TOFU).
        
        Args:
            peer_ip: IP address of the peer
            peer_port: Port of the peer
            mode: Connection mode ("client" or "server")
            
        Returns:
            True if verification successful, False otherwise
        """
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
        """Initialize connection renewal tracking variables."""
        self._message_count = 0
        self._last_renewal_time = datetime.now()

    def _renewal_monitor(self) -> None:
        """Monitor connection for renewal conditions."""
        while self.connected and not self._stop_flag.is_set():
            time.sleep(60)  # Check every minute
            
            if self._should_renew_connection():
                self._trigger_reconnection()

    def _should_renew_connection(self) -> bool:
        """Check if connection should be renewed."""
        if not self._last_renewal_time:
            return False
            
        time_elapsed = (datetime.now() - self._last_renewal_time).total_seconds() / 60
        return (self._message_count >= self.RENEW_AFTER_MESSAGES or 
                time_elapsed >= self.RENEW_AFTER_MINUTES)

    def _trigger_reconnection(self) -> None:
        """Trigger connection renewal."""
        if self._reconnect_in_progress.is_set():
            return
            
        self._reconnect_in_progress.set()
        self.message_callback("Renewing connection...")
        
        try:
            # Store current connection details
            old_peer_details = self._peer_connection_details
            old_is_server = self._is_server_mode
            
            # Close current connection
            self._stop_peer_connection()
            
            # Reconnect
            if old_is_server:
                # Wait for new incoming connection
                time.sleep(2)
            else:
                # Reconnect as client
                if old_peer_details:
                    peer_ip, peer_port = old_peer_details
                    if self._is_onion_address(peer_ip):
                        self.connect_to_onion_peer(peer_ip, self.crypto.get_peer_fingerprint(), peer_port)
                    else:
                        self.connect_to_peer(peer_ip, peer_port)
                        
        finally:
            self._reconnect_in_progress.clear()

    def _is_onion_address(self, address: str) -> bool:
        """Check if address is an onion address."""
        return address.endswith('.onion')

    def _stop_peer_connection(self) -> None:
        """Stop the current peer connection (session only)."""
        print(f"[LOG] Closing P2P peer connection (if any) on port {self.listen_port}")
        self.connected = False
        self._close_peer_socket()
        # Stop threads
        if self._receive_thread and self._receive_thread.is_alive():
            self._receive_thread.join(timeout=1)
        if self._renewal_thread and self._renewal_thread.is_alive():
            self._renewal_thread.join(timeout=1)
        print(f"[LOG] P2P peer connection closed (port {self.listen_port})")

    def _receive_messages(self) -> None:
        """Thread for receiving and processing messages."""
        while self.connected and not self._stop_flag.is_set():
            try:
                if not self.peer_socket:
                    break
                    
                encrypted_data = self._receive_raw()
                if not encrypted_data:
                    break
                    
                message = self.crypto.decrypt_message(encrypted_data)
                
                # Handle ping/pong
                if self._handle_ping_pong(message):
                    continue
                
                # Handle file transfer
                if self._handle_file_transfer(message):
                    continue
                
                # Handle disconnect
                if message.strip() == "__DISCONNECT__":
                    self.message_callback(Fore.LIGHTYELLOW_EX + "[INFO] The peer has disconnected." + Style.RESET_ALL)
                    self.stop()
                    return

                # Regular message
                self._message_count += 1
                self.message_callback(f"[{self._get_peer_nickname()}  |  {datetime.now().strftime('%H:%M:%S')}] {message}")
                
            except Exception as e:
                if not self._stop_flag.is_set():
                    self.message_callback(f"Error receiving message: {str(e)}")
                    break

    def _handle_ping_pong(self, message: str) -> bool:
        """Handle ping/pong messages."""
        if message.startswith("__PING__"):
            ping_id = message[8:]
            pong_response = f"__PONG__{ping_id}"
            self.send_message(pong_response)
            return True
        elif message.startswith("__PONG__"):
            ping_id = message[8:]
            with self._ping_lock:
                if ping_id in self._ping_responses:
                    self._ping_responses[ping_id] = time.time()
            return True
        return False

    def ping_peer(self, timeout: float = 5.0) -> Optional[float]:
        """
        Ping the connected peer and return response time.
        
        Args:
            timeout: Timeout in seconds
            
        Returns:
            Response time in seconds, or None if failed
        """
        if not self.connected:
            return None
            
        ping_id = str(int(time.time() * 1000))
        ping_message = f"__PING__{ping_id}"
        
        with self._ping_lock:
            self._ping_responses[ping_id] = None
            
        start_time = time.time()
        self.send_message(ping_message)
        
        # Wait for response
        while time.time() - start_time < timeout:
            with self._ping_lock:
                if self._ping_responses.get(ping_id) is not None:
                    response_time = self._ping_responses.pop(ping_id) - start_time
                    return response_time
            time.sleep(0.01)
            
        # Timeout
        with self._ping_lock:
            self._ping_responses.pop(ping_id, None)
        return None

    def _get_peer_nickname(self) -> str:
        """Get the nickname of the connected peer."""
        try:
            peer_fingerprint = self.crypto.get_peer_fingerprint()
            nickname = self.hosts_manager.get_nickname(peer_fingerprint)
            return nickname if nickname else peer_fingerprint[:8]
        except:
            return "Unknown"

    def send_message(self, message: str) -> None:
        """Send an encrypted message to the peer."""
        if not self.connected or not self.peer_socket:
            return
            
        try:
            encrypted_data = self.crypto.encrypt_message(message)
            self._send_raw(encrypted_data)
        except Exception as e:
            self.message_callback(f"Error sending message: {str(e)}")

    def send_file(self, file_path: str, callback=None) -> None:
        """
        Send a file to the peer.
        
        Args:
            file_path: Path to the file to send
            callback: Progress callback function
        """
        if not os.path.exists(file_path):
            self.message_callback(f"File not found: {file_path}")
            return
            
        file_size = os.path.getsize(file_path)
        file_name = os.path.basename(file_path)
        
        # Send file request
        request_data = {
            "file_name": file_name,
            "file_size": file_size
        }
        self.send_message(f"__FILE_REQUEST__{request_data}")
        
        # Store file path for when peer accepts
        self._pending_file_path = file_path

    def send_file_data(self, file_path: str, callback=None) -> None:
        """Send file data after peer accepts."""
        try:
            with open(file_path, 'rb') as f:
                while True:
                    chunk = f.read(8192)  # 8KB chunks
                    if not chunk:
                        break
                        
                    encrypted_chunk = self.crypto.encrypt_bytes(chunk)
                    self._send_raw(encrypted_chunk)
                    
                    if callback:
                        callback(f.tell() / os.path.getsize(file_path))
                        
            self.send_message("__FILE_END__")
            
        except Exception as e:
            self.message_callback(f"Error sending file: {str(e)}")

    def _handle_file_transfer(self, message: str) -> bool:
        """Handle file transfer protocol messages."""
        if message.startswith("__FILE_REQUEST__"):
            import ast
            req = ast.literal_eval(message[len("__FILE_REQUEST__"):])
            file_name = req['file_name']
            file_size = req['file_size']
            self.message_callback(f"Peer wants to send you a file: {file_name} ({file_size} bytes)")
            return True
        elif message.startswith("__FILE_ACCEPT__"):
            self.message_callback("Peer accepted file transfer. Sending file...")
            return True
        elif message.startswith("__FILE_DECLINE__"):
            self.message_callback("Peer declined the file transfer.")
            return True
        elif message.startswith("__FILE_END__"):
            self.message_callback("File transfer completed.")
            return True
        return False

    def receive_file(self, file_name: str, file_size: int, save_dir: str = "received_files", callback=None) -> str:
        """
        Receive a file from the peer.
        
        Args:
            file_name: Name of the file to receive
            file_size: Size of the file in bytes
            save_dir: Directory to save the file
            callback: Progress callback function
            
        Returns:
            Path to the saved file
        """
        os.makedirs(save_dir, exist_ok=True)
        file_path = os.path.join(save_dir, file_name)
        
        with open(file_path, 'wb') as f:
            received_size = 0
            while received_size < file_size:
                chunk = self._receive_raw()
                if not chunk:
                    break
                    
                decrypted_chunk = self.crypto.decrypt_bytes(chunk)
                f.write(decrypted_chunk)
                received_size += len(decrypted_chunk)
                
                if callback:
                    callback(received_size / file_size)
                    
        return file_path

    def _send_raw(self, data: bytes) -> None:
        """Send raw data to the peer."""
        if self.peer_socket:
            length = len(data)
            self.peer_socket.send(length.to_bytes(4, 'big'))
            self.peer_socket.send(data)

    def _receive_raw(self) -> bytes:
        """Receive raw data from the peer."""
        if not self.peer_socket:
            return b''
            
        try:
            # Receive length
            length_bytes = self.peer_socket.recv(4)
            if not length_bytes:
                return b''
            length = int.from_bytes(length_bytes, 'big')
            
            # Receive data
            data = b''
            while len(data) < length:
                chunk = self.peer_socket.recv(length - len(data))
                if not chunk:
                    return b''
                data += chunk
                
            return data
        except Exception:
            return b''

    def _close_peer_socket(self) -> None:
        """Close the peer socket cleanly."""
        if self.peer_socket:
            try:
                self.peer_socket.shutdown(socket.SHUT_RDWR)
            except Exception:
                pass  # Peut déjà être fermé
            try:
                self.peer_socket.close()
            except Exception:
                pass
            self.peer_socket = None

    def stop(self) -> None:
        """Stop only the peer connection, not the server socket."""
        print(f"[LOG] Stopping P2P peer connection (not the server) on port {self.listen_port}...")
        self._stop_peer_connection()
        print(f"[LOG] P2P peer connection stopped (server still listening on port {self.listen_port})")

    def close_server(self) -> None:
        """Close the server socket (to be called only at application exit)."""
        print(f"[LOG] Closing P2P server socket on port {self.listen_port}")
        self._server_running = False
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None
        if self._accept_thread and self._accept_thread.is_alive():
            self._accept_thread.join(timeout=2)
        print(f"[LOG] P2P server socket closed (port {self.listen_port})")

    def _validate_ip_address(self, ip: str) -> bool:
        """Validate IP address format."""
        try:
            ipaddress.ip_address(ip)
            return True
        except ValueError:
            return False

    def _is_private_ip(self, ip: str) -> bool:
        """Check if IP address is private."""
        try:
            ip_obj = ipaddress.ip_address(ip)
            return ip_obj.is_private
        except ValueError:
            return False 