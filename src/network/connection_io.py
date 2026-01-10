# Low-level socket I/O mixin for P2PConnection

class IOMixin:
    """
    Mixin for low-level socket I/O in P2PConnection.
    """
    def _send_raw(self, data: bytes, transmission_type = b"GEN") -> None:
        """
        Send raw data to the peer.
        Args:
            data: Bytes to send.
            transmission_type: Type of transmission ('GEN' for general).
        """
        if self.peer_socket:
            data_to_send = transmission_type + b':' + data
            length = len(data_to_send)
            self.peer_socket.send(length.to_bytes(4, 'big'))
            self.peer_socket.send(data_to_send)

    def _receive_raw(self) -> bytes:
        """
        Receive raw data from the peer.
        Returns:
            Bytes received, or empty bytes if error.
        """
        if not self.peer_socket:
            return b''
        try:
            length_bytes = self.peer_socket.recv(4)
            if not length_bytes:
                return b''
            length = int.from_bytes(length_bytes, 'big')
            data_raw = b''
            while len(data_raw) < length:
                chunk = self.peer_socket.recv(length - len(data_raw))
                if not chunk:
                    return b''
                data_raw += chunk
            transmission_type, data = data_raw.split(b':', 1)
            #print("Received transmission type:", type(transmission_type))
            #print("Received data length:", len(data))
            #print("Data type:", type(data))
            return data, transmission_type
        except Exception:
            return b''

    def _close_peer_socket(self) -> None:
        """
        Close the peer socket cleanly.
        """
        if self.peer_socket:
            try:
                self.peer_socket.shutdown(2)
            except Exception:
                pass
            try:
                self.peer_socket.close()
            except Exception:
                pass
            self.peer_socket = None 