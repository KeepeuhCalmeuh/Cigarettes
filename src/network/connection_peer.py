# Peer connection management mixin for P2PConnection
import socket
import threading
import socks
from colorama import Fore, Style
from datetime import datetime

class PeerMixin:
    """
    Mixin for peer connection management (client/server) in P2PConnection.
    """
    def connect_to_peer(self, peer_ip: str, peer_port: int, timeout: int = 10) -> bool:
        """
        Connect to a remote peer with authentication.
        Args:
            peer_ip: IP address of the peer.
            peer_port: Port of the peer.
            timeout: Connection timeout in seconds.
        Returns:
            True if connection successful, False otherwise.
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
            self.message_callback(Fore.LIGHTYELLOW_EX + f"[{datetime.now().strftime('%H:%M:%S')}] Attempting to connect to {peer_ip}:{peer_port}..." + Style.RESET_ALL)
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
            onion_address: Onion address of the peer.
            fingerprint: Expected fingerprint of the peer.
            port: Port number.
            timeout: Connection timeout in seconds.
        Returns:
            True if connection successful, False otherwise.
        """
        if self.connected: 
            self.message_callback("Already connected to a peer")
            return False
        self._stop_peer_connection()
        self._peer_connection_details = (onion_address, port)
        self._is_server_mode = False
        try:
            self.message_callback(Fore.LIGHTYELLOW_EX + f"[{datetime.now().strftime('%H:%M:%S')}] Attempting to connect to {onion_address}:{port} via Tor..." + Style.RESET_ALL)
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
        """
        Thread for accepting incoming connections with authentication.
        """
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
                #self.peer_socket.settimeout(5)  # Timeout pour éviter blocage sur recv
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