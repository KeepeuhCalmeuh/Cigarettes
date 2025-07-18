import threading
import sys
from typing import Optional
from connection import P2PConnection
from datetime import datetime
from known_hosts_manager import get_nickname, set_nickname, add_host, list_known_hosts
import os
from colorama import Fore, Style

try:
    import keyboard
    KEYBOARD_AVAILABLE = True
except ImportError:
    KEYBOARD_AVAILABLE = False


class ConsoleUI:
    def __init__(self):
        self.connection: Optional[P2PConnection] = None
        self._stop_flag = threading.Event()
        self.history = []  # Discussion history
        self._multiline_mode = False
        self._current_message = []
        
    def display_help(self):
        """Displays help for available commands"""
        print("\nAvailable Commands :")
        print("  /connect <peer_onion_adress> <PEER_FINGERPRINT> <peer_listening_port (optional, default : 34567)>                       - Connect to a remote peer")
        print("  /status                                    - Display connection status and peer information")
        print("  /stop                                      - Disconnect from the peer without exiting the application")
        print("  /save                                      - Save the discussion history to a .txt file")
        print("  /ping                                      - Ping the connected peer and display response time")
        print("  /info                                      - Displays your fingerprint, .onion address and listening port")
        print("  /rename <fingerprint> <new_name>           - Rename a peer in known hosts")
        print("  /addHost <peer_onion_adress> <fingerprint> - Add a host to known hosts")
        print("  /removehost <peer_onion_adress>            - Remove a host from known hosts")
        print("  /listHosts                                 - List all known hosts")
        print("  /multiline                                 - Toggle multi-line message mode (use Shift+Enter for new line, Enter to send, CANCEL to cancel)")
        print("  /help                                      - Displays this help")
        print("  /exit                                      - Exit the application")

        print("\nTo send a message, simply type it and press Enter.")
        print("Waiting for connection on the specified port...\n")

    def handle_message(self, message: str):
        """Callback to display received messages with timestamp and save in history, and handle file transfer protocol."""
        now = datetime.now().strftime("%H:%M:%S")
        # File transfer protocol handling
        if hasattr(self, '_pending_file') and self._pending_file.get('status') == 'waiting':
            # Handle peer response to file request
            if message.startswith("__FILE_ACCEPT__"):
                print(Fore.LIGHTGREEN_EX + f"[INFO] Peer accepted file transfer. Sending file..." + Style.RESET_ALL)
                self._pending_file['status'] = 'sending'
                self.connection.send_file_data(self._pending_file['file_path'], callback=lambda p: print(Fore.LIGHTCYAN_EX + f"[INFO] Sending progress: {p*100:.1f}%" + Style.RESET_ALL, end='\r'))
                print(Fore.LIGHTGREEN_EX + f"[INFO] File sent successfully!" + Style.RESET_ALL)
                del self._pending_file
                return
            elif message.startswith("__FILE_DECLINE__"):
                print(Fore.LIGHTRED_EX + f"[INFO] Peer declined the file transfer." + Style.RESET_ALL)
                del self._pending_file
                return
        # Handle incoming file request
        if message.startswith("__FILE_REQUEST__"):
            import ast
            req = ast.literal_eval(message[len("__FILE_REQUEST__"):])
            file_name = req['file_name']
            file_size = req['file_size']
            print(Fore.LIGHTYELLOW_EX + f"[INFO] Peer wants to send you a file: {file_name} ({file_size} bytes)" + Style.RESET_ALL)
            resp = input(Fore.LIGHTYELLOW_EX + "Do you want to accept the file? (y/n): " + Style.RESET_ALL).strip().lower()
            if resp == 'y':
                print(Fore.LIGHTGREEN_EX + f"[INFO] You accepted the file. Receiving..." + Style.RESET_ALL)
                self.connection.send_message("__FILE_ACCEPT__")
                # Receive file
                path = self.connection.receive_file(file_name, file_size, save_dir="received_files", callback=lambda p: print(Fore.LIGHTCYAN_EX + f"[INFO] Receiving progress: {p*100:.1f}%" + Style.RESET_ALL, end='\r'))
                print(Fore.LIGHTGREEN_EX + f"\n[INFO] File received and saved to: {path}" + Style.RESET_ALL)
            else:
                print(Fore.LIGHTRED_EX + f"[INFO] You declined the file." + Style.RESET_ALL)
                self.connection.send_message("__FILE_DECLINE__")
            return
        if message.startswith("__FILE_END__"):
            print(Fore.LIGHTGREEN_EX + f"[INFO] File transfer completed." + Style.RESET_ALL)
            return
        # Handle multi-line received messages
        if '\n' in message:
            lines = message.split('\n')
            line = f"{lines[0]}"
            print(f"\n{line}")
            for additional_line in lines[1:]:
                print(f"{'':>10} {additional_line}")
            
            # Save to history with proper formatting
            history_entry = f"{message}"
            self.history.append(history_entry)
        else:
            line = f"{message}"
            print(f"\n{line}")
            self.history.append(line)
        
        self._display_prompt()

    def _display_prompt(self):
        """Displays the appropriate prompt based on mode"""
        if self._multiline_mode:
            sys.stdout.write(">> ")
        else:
            sys.stdout.write("> ")
        sys.stdout.flush()

    def _get_multiline_input_advanced(self) -> str:
        """
        Advanced multi-line input using keyboard library.
        Shift+Enter for new line, Enter to send.
        """
        if not KEYBOARD_AVAILABLE:
            print("Multi-line mode requires the 'keyboard' library.")
            print("Install it with: pip install keyboard")
            print("Note: On Linux, you may need to run with sudo or configure permissions.")
            return ""

        print("Multi-line mode: Shift+Enter for new line, Enter to send, Ctrl+C to cancel")
        print("---")
        
        lines = []
        current_line = ""
        
        try:
            while True:
                event = keyboard.read_event()
                if event.event_type == keyboard.KEY_DOWN:
                    key = event.name
                    
                    # Handle Ctrl+C (cancel)
                    if key == 'c' and keyboard.is_pressed('ctrl'):
                        print("\nMulti-line input cancelled.")
                        return ""
                    
                    # Handle Shift+Enter (new line)
                    elif key == 'enter' and keyboard.is_pressed('shift'):
                        lines.append(current_line)
                        current_line = ""
                        print()  # New line in display
                        
                    # Handle Enter (send message)
                    elif key == 'enter':
                        if current_line or lines:
                            lines.append(current_line)
                            break
                        else:
                            print("Empty message not sent.")
                            return ""
                    
                    # Handle Backspace
                    elif key == 'backspace':
                        if current_line:
                            current_line = current_line[:-1]
                            # Clear current line and reprint
                            print(f'\r{" " * (len(current_line) + 10)}\r', end='')
                            print(current_line, end='')
                        elif lines:
                            # If current line is empty, go back to previous line
                            current_line = lines.pop()
                            print(f'\r{" " * 50}\r', end='')
                            print(current_line, end='')
                    
                    # Handle printable characters
                    elif len(key) == 1:
                        current_line += key
                        print(key, end='')
                    
                    # Handle space
                    elif key == 'space':
                        current_line += ' '
                        print(' ', end='')
                        
                    sys.stdout.flush()
                        
        except KeyboardInterrupt:
            print("\nMulti-line input cancelled.")
            return ""
        
        message = '\n'.join(lines)
        print("\n---")
        return message

    def _get_multiline_input_simple(self) -> str:
        """
        Simple multi-line input fallback.
        Type lines, empty line to send.
        """
        print("Multi-line mode: Enter empty line to send, type 'CANCEL' to cancel")
        print("---")
        
        lines = []
        
        try:
            while True:
                line = input()
                
                if line.strip().upper() == "CANCEL":
                    print("Multi-line message cancelled.")
                    return ""
                
                if line.strip() == "":
                    if lines:
                        break
                    else:
                        print("Empty message not sent.")
                        return ""
                
                lines.append(line)
                        
        except (EOFError, KeyboardInterrupt):
            print("\nMulti-line input cancelled.")
            return ""
        
        message = '\n'.join(lines)
        print("---")
        return message

    def start(self, port: int):
        """Starts the console interface"""
        self.connection = P2PConnection(port, self.handle_message)
        self.connection.start_server()
        
        print(f"\nCigarettes - Encrypted P2P Messaging")
        print(f"Listening on the port {port}")
        print(f"Your fingerprint: {self.connection.crypto.get_public_key_fingerprint()}")
        self.display_help()
        
        # Start the thread reading user input        
        input_thread = threading.Thread(target=self._input_loop, daemon=True)
        input_thread.start()
        
        try:
            # Waiting the user wants to exit
            self._stop_flag.wait()
        except KeyboardInterrupt:
            pass
        finally:
            if self.connection:
                self.connection.stop()

    def _input_loop(self):
        """Loop for reading user input"""
        while not self._stop_flag.is_set():
            try:
                if self._multiline_mode and KEYBOARD_AVAILABLE:
                    # Use advanced multi-line input
                    self._display_prompt()
                    message = self._get_multiline_input_advanced()
                    if message:
                        self._send_message(message)
                else:
                    # Standard single-line input
                    self._display_prompt()
                    user_input = input().strip()
                    
                    if not user_input:
                        continue
                    
                    if user_input.startswith("/"):
                        self._handle_command(user_input)
                    elif self.connection.connected:
                        self._send_message(user_input)
                    else:
                        print("Not connected. Use /connect <peer_onion_adress> <PEER_FINGERPRINT> <peer_listening_port (optional, default : 34567)> to connect to a peer.")
            
            except EOFError:
                break
            except Exception as e:
                print(f"Error: {str(e)}")

    def _send_message(self, message: str):
        """Sends a message and handles display/history"""
        if not message:
            return
            
        now = datetime.now().strftime("%H:%M:%S")
        
        # Display the message
        if '\n' in message:
            lines = message.split('\n')
            print(Fore.YELLOW + f"[You | {now}] {lines[0]}" + Style.RESET_ALL)
            for line in lines[1:]:
                print(f"{'':>15} {line}")
        else:
            print(Fore.YELLOW + f"[You | {now}] {message}" + Style.RESET_ALL)
        
        # Add to history
        history_entry = f"[You | {now}] {message}"
        self.history.append(history_entry)
        
        # Send the message
        self.connection.send_message(message)

    def _handle_command(self, command: str):
        """Manages special orders"""
        parts = command.split()
        cmd = parts[0].lower()

        if cmd == "/help":
            self.display_help()

        elif cmd == "/multiline":
            if not KEYBOARD_AVAILABLE:
                message = self._get_multiline_input_simple()
                if message and self.connection.connected:
                    self._send_message(message)
                elif not self.connection.connected:
                    print("Not connected. Use /connect <ip> <port> to connect to a peer.")
            else:
                self._multiline_mode = not self._multiline_mode
                if self._multiline_mode:
                    print("Multi-line mode ON: Shift+Enter for new line, Enter to send")
                else:
                    print("Multi-line mode OFF: Enter to send single-line messages")

        elif cmd == "/stop":
            if self.connection and self.connection.connected:
                try:
                    # Notify the peer
                    self.connection.send_message("[INFO] The peer has terminated the connection.")
                except Exception:
                    pass
                # Only stop the peer connection, not the entire server
                self.history = [] #reset history
                self.connection._stop_peer_connection()
                print("Connection to peer completed.")
            else:
                print("No active connections to close.")

        elif cmd == "/exit":
            print("Bye!")
            self._stop_flag.set()

        elif cmd == "/info":
            if self.connection:
                print(f"Your fingerprint: {self.connection.crypto.get_public_key_fingerprint()}")
                print(f"Your .onion address: {self.connection.crypto.get_onion_address()}")
                print(f"Your listening port: {self.connection.listen_port}")
            if self.connection.connected:
                print(f"Connected to: {self.connection.peer_ip}:{self.connection.peer_port}")
            else:
                print("Not connected.")


        elif cmd == "/connect":
            # Connection via .onion and fingerprint
            if len(parts) == 3 and parts[1].endswith(".onion"):
                onion_address = parts[1]
                fingerprint = parts[2]
                port = 34567  # Default port for Tor Hidden Service
                if self.connection.connected:
                    print("Already connected to a peer.")
                    return
                print(f"Attempting to connect to {onion_address}:{port} via Tor...")
                if self.connection.connect_to_onion_peer(onion_address, fingerprint, port):
                    print("Connected successfully via Tor!")
                return
            # Classic connection IP:port
            if len(parts) < 3:
                print("Usage: /connect <ip> <port> [timeout] or /connect <onion> <fingerprint>")
                print("Example: /connect 192.168.1.100 8080")
                print("Example: /connect mwrl7yek4bsdk4scm2gigwkl3emqitz622hjcb65aastrku5ytse6qd.onion eafa04cfe3c8ba6006d3979c1de1943b5f47f77c3f77283de7e410a1e2e1400d")
                return

            try:
                ip = parts[1]
                port = int(parts[2])
                timeout = int(parts[3]) if len(parts) > 3 else 10
                
                if self.connection.connected:
                    print("Already connected to a peer.")
                    return
                
                print(f"Attempting to connect to {ip}:{port} (timeout: {timeout}s)...")
                if self.connection.connect_to_peer(ip, port, timeout):
                    print("Connected successfully!")
            
            except ValueError:
                print("Port and timeout must be numbers.")
            
        elif cmd == "/save":
            if not self.history:
                print("No messages to save.")
                return
            os.makedirs("history", exist_ok=True)
            filename = datetime.now().strftime("history_%Y%m%d_%H%M%S.txt")
            path = os.path.join("history", filename)
            try:
                with open(path, "w", encoding="utf-8") as f:
                    for line in self.history:
                        f.write(line + "\n")
                self.connection.send_message(f"[INFO] Discussion history saved by peer.")
                print(f"History saved in {path}")
            except Exception as e:
                print(f"Error while saving:{e}")

        elif cmd == "/listhosts" or cmd == "/listhosts":
            list_known_hosts()

        elif command.startswith("/rename "):
            parts = command.split(" ", 2)
            if len(parts) != 3:
                print("Usage: /rename <fingerprint> <new_name>")
                return
            fingerprint, new_name = parts[1], parts[2]
            try:
                set_nickname(fingerprint, new_name)
                print(f"Updated {fingerprint} peer name: {new_name}")
                if self.connection.connected and self.connection.peer_fingerprint == fingerprint:
                    self.connection.send_message(f"[INFO] Peer renamed you as {new_name}.")
            except Exception as e:
                print(f"Error while renaming: {e}")

        elif command.startswith("/addHost ") or command.startswith("/addhost "):
            parts = command.split(" ", 2)
            if len(parts) != 3:
                print("Usage: /addHost <ip:port> <fingerprint>")
                return
            ip_port, fingerprint = parts[1], parts[2]
            try:
                add_host(ip_port, fingerprint)
            except Exception as e:
                print(f"Error adding host: {e}")
        
        elif command.startswith("/removehost ") or command.startswith("/removeHost "):
            parts = command.split(" ", 1)
            if len(parts) != 2:
                print("Usage: /removehost <peer_onion_adress>")
                return
            ip_port = parts[1]
            try:
                if self.connection.connected:
                    self.connection.send_message(f"[INFO] Peer removed you from known hosts.")
                add_host(ip_port, None)  # Remove host by setting fingerprint to None
                print(f"Host {ip_port} removed from known hosts.")
            except Exception as e:
                print(f"Error removing host: {e}")

        elif cmd == "/ping":
            if not self.connection or not self.connection.connected:
                print("Not connected. Use /connect <peer_onion_adress> <PEER_FINGERPRINT> <peer_listening_port (optional, default : 34567)> to connect to a peer.")
                return
            try:
                print(f"Ping : {self.connection.ping_peer():.2f} ms")
            except Exception as e:
                print(f"Error during ping: {e}")

        elif cmd == "/status":
            if self.connection:
                print(f"Listen port: {self.connection.listen_port}")
                print(f"Connected: {self.connection.connected}")
                if self.connection.connected and self.connection._peer_connection_details:
                    ip, port = self.connection._peer_connection_details
                    print(f"Peer: {ip}:{port}")
                    print(f"Mode: {'Server' if self.connection._is_server_mode else 'Client'}")
                    print(f"Messages échangés : {self.connection._message_count}")

        elif cmd == "/send_file":
            # /send_file <file_path>
            if not self.connection or not self.connection.connected:
                print(Fore.LIGHTRED_EX + "[ERROR] Not connected to a peer. Use /connect first." + Style.RESET_ALL)
                return
            if len(parts) != 2:
                print(Fore.LIGHTYELLOW_EX + "Usage: /send_file <file_path>" + Style.RESET_ALL)
                return
            file_path = parts[1]
            import os
            if not os.path.isfile(file_path):
                print(Fore.LIGHTRED_EX + f"[ERROR] File not found: {file_path}" + Style.RESET_ALL)
                return
            # Send file request to peer
            print(Fore.LIGHTCYAN_EX + f"[INFO] Sending file request for '{file_path}'..." + Style.RESET_ALL)
            self.connection.send_file(file_path)
            # Wait for peer response in handle_message
            self._pending_file = {
                "file_path": file_path,
                "status": "waiting"
            }
            return

        else:
            print(f"Unknown command. Type /help for a list of commands.")