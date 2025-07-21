"""
Base P2P connection management: serveur, état général, arrêt.
"""

import socket
import threading
from typing import Callable, Optional, Tuple
from datetime import datetime
import os
from colorama import Fore, Style
import socks

from ..core.crypto import CryptoManager
from ..core.hosts import KnownHostsManager

class P2PConnection:
    """
    Manages P2P connections with encryption, authentication, and file transfer capabilities.
    (Base: serveur, état, arrêt)
    """
    RENEW_AFTER_MESSAGES = 10000
    RENEW_AFTER_MINUTES = 60

    def __init__(self, listen_port: int, message_callback: Callable[[str], None]):
        self.listen_port = listen_port
        self.message_callback = message_callback
        self.crypto = CryptoManager()
        self.hosts_manager = KnownHostsManager()
        self.connected = False
        self.socket: Optional[socket.socket] = None
        self.peer_socket: Optional[socket.socket] = None
        self._stop_flag = threading.Event()
        self._server_running = False
        self._message_count = 0
        self._last_renewal_time: Optional[datetime] = None
        self._peer_connection_details: Optional[Tuple[str, int]] = None
        self._is_server_mode = False
        self._reconnect_in_progress = threading.Event()
        self._accept_thread: Optional[threading.Thread] = None
        self._receive_thread: Optional[threading.Thread] = None
        self._renewal_thread: Optional[threading.Thread] = None
        self._ping_responses = {}
        self._ping_lock = threading.Lock()
        self._pending_file_path = None

    def start_server(self) -> None:
        if self._server_running:
            return
        self._stop_flag.clear()
        self._server_running = True
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind(('0.0.0.0', self.listen_port))
            self.socket.listen(1)
            self._is_server_mode = True
            self._accept_thread = threading.Thread(target=self._accept_connections, daemon=True)
            self._accept_thread.start()
        except Exception as e:
            self.message_callback(f"Failed to start server: {str(e)}")
            self._server_running = False
            if self.socket:
                self.socket.close()
                self.socket = None

    def stop(self) -> None:
        self._stop_peer_connection()

    def close_server(self) -> None:
        self._server_running = False
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None
        if self._accept_thread and self._accept_thread.is_alive():
            self._accept_thread.join(timeout=2)

    def _stop_peer_connection(self) -> None:
        """Stop the current peer connection (session only)."""
        self.connected = False
        self._close_peer_socket()
        # Stop threads
        if self._receive_thread and self._receive_thread.is_alive():
            self._receive_thread.join(timeout=1)
        if self._renewal_thread and self._renewal_thread.is_alive():
            self._renewal_thread.join(timeout=1) 