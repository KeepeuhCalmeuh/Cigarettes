# File transfer management mixin for P2PConnection
import os

class FileTransferMixin:
    """
    Mixin for file sending/receiving in P2PConnection.
    """
    def send_file(self, file_path: str, callback=None) -> None:
        """
        Send a file to the peer.
        Args:
            file_path: Path to the file to send.
            callback: Progress callback function.
        """
        if not os.path.exists(file_path):
            self.message_callback(f"File not found: {file_path}")
            return
        file_size = os.path.getsize(file_path)
        file_name = os.path.basename(file_path)
        request_data = {
            "file_name": file_name,
            "file_size": file_size
        }
        self.send_message(f"__FILE_REQUEST__{request_data}")
        self._pending_file_path = file_path

    def send_file_data(self, file_path: str, callback=None) -> None:
        """
        Send file data after peer accepts.
        Args:
            file_path: Path to the file to send.
            callback: Progress callback function.
        """
        try:
            with open(file_path, 'rb') as f:
                while True:
                    chunk = f.read(8192)
                    if not chunk:
                        break
                    encrypted_chunk = self.crypto.encrypt_bytes(chunk)
                    self._send_raw(encrypted_chunk)
                    if callback:
                        callback(f.tell() / os.path.getsize(file_path))
            self.send_message("__FILE_END__")
        except Exception as e:
            self.message_callback(f"Error sending file: {str(e)}")

    def receive_file(self, file_name: str, file_size: int, save_dir: str = "received_files", callback=None) -> str:
        """
        Receive a file from the peer.
        Args:
            file_name: Name of the file to receive.
            file_size: Size of the file in bytes.
            save_dir: Directory to save the file.
            callback: Progress callback function.
        Returns:
            Path to the saved file.
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

    def _handle_file_transfer(self, message: str) -> bool:
        """
        Handle file transfer protocol messages.
        Args:
            message: Message to check for file transfer protocol.
        Returns:
            True if handled as file transfer protocol, False otherwise.
        """
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