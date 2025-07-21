# Gestion bas niveau des sockets pour P2PConnection

class IOMixin:
    def _send_raw(self, data: bytes) -> None:
        if self.peer_socket:
            length = len(data)
            self.peer_socket.send(length.to_bytes(4, 'big'))
            self.peer_socket.send(data)

    def _receive_raw(self) -> bytes:
        if not self.peer_socket:
            return b''
        try:
            length_bytes = self.peer_socket.recv(4)
            if not length_bytes:
                return b''
            length = int.from_bytes(length_bytes, 'big')
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