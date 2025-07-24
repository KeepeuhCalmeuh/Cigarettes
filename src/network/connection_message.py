# Message and ping management mixin for P2PConnection
from datetime import datetime
from re import A
import time
from colorama import Fore, Style
import src.core.file_transfer as file_transfer

class MessageMixin:
    """
    Mixin for message and ping management in P2PConnection.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._receiving_file = False  # Always initialize here to avoid attribute errors
        self._file_receive_info = None  # dict: name, size, received, file_obj

    def _receive_messages(self) -> None:
        """
        Thread for receiving and processing messages.
        """
        while self.connected and not self._stop_flag.is_set():
            print("ON EST DANS LE _RECEIVE_MESSAGES et le _receiving_file est 3", self._receiving_file)
            try:
                print("ON EST PAS ENCORE DANS LE MODE RECEPTION DE FICHIER et le _receiving_file est 4", self._receiving_file)
                if not self.peer_socket:
                    break
                # Binary file receiving mode
                
                if self._receiving_file:
                    print("ON EST DANS LE MODE RECEPTION DE FICHIER")
                    # If the protocol was reset (declined or completed), exit file receiving mode
                    if not file_transfer.FILE_TRANSFER_BOOL:
                        self._receiving_file = False
                        self._file_receive_info = None
                    else:
                        encrypted_chunk = self._receive_raw()
                        if not encrypted_chunk:
                            self.message_callback("> [ERROR] Connection lost during file transfer.")
                            self._receiving_file = False
                            if self._file_receive_info and self._file_receive_info['file_obj']:
                                self._file_receive_info['file_obj'].close()
                            break
                        chunk = self.crypto.decrypt_bytes(encrypted_chunk)
                        self._file_receive_info['file_obj'].write(chunk)
                        self._file_receive_info['received'] += len(chunk)
                        # Progress bar display
                        percent = self._file_receive_info['received'] / self._file_receive_info['size']
                        bar_len = 30
                        filled_len = int(bar_len * percent)
                        bar = '#' * filled_len + '-' * (bar_len - filled_len)
                        print(Fore.LIGHTYELLOW_EX + f"\r> [RECEIVING] |{bar}| {percent*100:5.1f}%" + Style.RESET_ALL, end='')
                        if self._file_receive_info['received'] >= self._file_receive_info['size']:
                            self._file_receive_info['file_obj'].close()
                            print(Fore.LIGHTGREEN_EX + f"\n> [INFO] File received successfully and saved to received_files/{self._file_receive_info['name']}" + Style.RESET_ALL)
                            file_transfer.reset_all_file_transfer_state()
                            self._receiving_file = False
                            self._file_receive_info = None
                        continue
                else:
                    encrypted_data = self._receive_raw()
                    if not encrypted_data:
                        self.message_callback(Fore.LIGHTYELLOW_EX + "[INFO] The peer has closed the connection or disconnected." + Style.RESET_ALL)
                        self.stop()
                        break
                    message = self.crypto.decrypt_message(encrypted_data)
                    # Detection of file transfer acceptance (activate file receiving mode)
                    if "__FILE_TRANSFER_ACCEPTED__" in message:
                        if self._file_receive_info and self._file_receive_info['file_obj']:
                            self._receiving_file = True
                            continue
                    # Detection of file transfer request (store info but do not activate receiving mode)
                    if "__FILE_TRANSFER__" in message:
                        idx = message.index("__FILE_TRANSFER__")
                        file_info = message[idx + len("__FILE_TRANSFER__"):].strip().split()
                        if len(file_info) >= 2:
                            file_name = file_info[0]
                            try:
                                file_size = int(file_info[1])
                            except ValueError:
                                self.message_callback("> [ERROR] Invalid file transfer request.")
                                continue
                            import os
                            os.makedirs('received_files', exist_ok=True)
                            file_path = os.path.join('received_files', file_name)
                            file_obj = open(file_path, 'wb')
                            self._file_receive_info = {
                                'name': file_name,
                                'size': file_size,
                                'received': 0,
                                'file_obj': file_obj
                            }
                            self.message_callback(message)
                            continue
                    if self._handle_ping_pong(message):
                        continue
                    if self._handle_file_transfer(message):
                        continue
                    if message.strip() == "__DISCONNECT__":
                        self.message_callback(Fore.LIGHTYELLOW_EX + "[INFO] The peer has disconnected." + Style.RESET_ALL)
                        self.stop()
                        return
                    self._message_count += 1
                    self.message_callback(f"[{self._get_peer_nickname()}  |  {datetime.now().strftime('%H:%M:%S')}] {message}")
            except Exception as e:
                if not self._stop_flag.is_set():
                    self.message_callback(f"Error receiving message: {str(e)}")
                    break

    def send_message(self, message: str) -> None:
        """
        Send an encrypted message to the peer.
        Args:
            message: Message to send.
        """
        if not self.connected or not self.peer_socket:
            return
        try:
            encrypted_data = self.crypto.encrypt_message(message)
            # print(f"Encrypted data: {encrypted_data}")
            self._send_raw(encrypted_data)
        except Exception as e:
            self.message_callback(f"Error sending message: {str(e)}")

    def ping_peer(self, timeout: float = 5.0) -> float:
        """
        Ping the connected peer and return response time.
        Args:
            timeout: Timeout in seconds.
        Returns:
            Response time in seconds, or None if failed.
        """
        if not self.connected:
            return None
        ping_id = str(int(time.time() * 1000))
        ping_message = f"__PING__{ping_id}"
        with self._ping_lock:
            self._ping_responses[ping_id] = None
        start_time = time.time()
        self.send_message(ping_message)
        while time.time() - start_time < timeout:
            with self._ping_lock:
                if self._ping_responses.get(ping_id) is not None:
                    response_time = self._ping_responses.pop(ping_id) - start_time
                    return response_time
            time.sleep(0.01)
        with self._ping_lock:
            self._ping_responses.pop(ping_id, None)
        return None

    def _handle_ping_pong(self, message: str) -> bool:
        """
        Handle ping/pong messages.
        Args:
            message: Message to check for ping/pong.
        Returns:
            True if handled as ping/pong, False otherwise.
        """
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

    def _handle_file_transfer(self, message: str) -> bool:
        """
        Handle file transfer messages.
        Args:
            message: Message to check for file transfer.
        Returns:
            True if handled as file transfer, False otherwise.
        """
        if message.startswith("__FILE_ACCEPT__"):
            self.activate_file_receiving_mode()
            print("ON MET LE MODE RECEPTION DE FICHIER A TRUE DANS LE FICHIER CONNECTION_MESSAGE.PY et le _receiving_file est 1", self._receiving_file)
            return True
        return False

    def activate_file_receiving_mode(self):
        """
        Activate file receiving mode so that the next incoming data is treated as a file chunk.
        Should be called when the user sends /__FILE_ACCEPT__.
        """
        if self._file_receive_info and self._file_receive_info['file_obj']:
            self._receiving_file = True
            print("ON MET LE MODE RECEPTION DE FICHIER A TRUE DANS LE FICHIER CONNECTION_MESSAGE.PY")

    def _get_peer_nickname(self) -> str:
        """
        Get the nickname of the connected peer.
        Returns:
            Nickname or short fingerprint, or 'Unknown'.
        """
        try:
            peer_fingerprint = self.crypto.get_peer_fingerprint()
            nickname = self.hosts_manager.get_nickname(peer_fingerprint)
            # print(f"Nickname: {nickname}")
            return nickname if nickname else peer_fingerprint[:8]
        except:
            return "Unknown" 