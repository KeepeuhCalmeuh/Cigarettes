import threading
import sys
from typing import Optional
from connection import P2PConnection
from datetime import datetime
from known_hosts_manager import get_nickname, set_nickname, add_host, list_known_hosts
import os
from colorama import Fore, Style
from local_ip_utils import get_public_ip_and_port

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
        print("  /connect <ip> <port>                       - Connect to a remote peer")
        print("  /status                                    - Display connection status and peer information")
        print("  /stop                                      - Disconnect from the peer without exiting the application")
        print("  /save                                      - Save the discussion history to a .txt file")
        print("  /ping                                      - Ping the connected peer and display response time")
        print("  /fingerprint                               - Displays the fingerprint of your public key")
        print("  /rename <fingerprint> <new_name>           - Rename a peer in known hosts")
        print("  /addHost <ip:port> <fingerprint>           - Add a host to known hosts")
        print("  /removehost <ip:port>                      - Remove a host from known hosts")
        print("  /listHosts                                 - List all known hosts")
        print("  /multiline                                 - Toggle multi-line message mode (use Shift+Enter for new line, Enter to send, CANCEL to cancel)")
        print("  /help                                      - Displays this help")
        print("  /exit                                      - Exit the application")

        print("\nTo send a message, simply type it and press Enter.")
        print("Waiting for connection on the specified port...\n")

    def handle_message(self, message: str):
        """Callback to display received messages with timestamp and save in history"""
        now = datetime.now().strftime("%H:%M:%S")
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
                        print("Not connected. Use /connect <ip> <port> to connect to a peer.")
            
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

        elif cmd == "/fingerprint":
            if self.connection:
                print(f"Your fingerprint: {self.connection.crypto.get_public_key_fingerprint()}")

        elif cmd == "/connect":
            if len(parts) < 3:
                print("Usage: /connect <ip> <port> [timeout]")
                print("Example: /connect 192.168.1.100 8080")
                print("Example: /connect 203.0.113.1 8080 15")
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

        elif cmd == "/listhosts":
            list_known_hosts()

        elif cmd == "/punch":
            if len(parts) != 3:
                print("Usage: /punch <ip> <port>")
                return
            ip = parts[1]
            try:
                port = int(parts[2])
                if self.connection.connected:
                    print("Already connected. Use /stop to disconnect first.")
                    return
                self.connection.start_hole_punch(ip, port)
                print("Tentative de connexion via hole punching lancée.")
            except ValueError:
                print("Port invalide.")

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

        elif command.startswith("/addHost "):
            parts = command.split(" ", 2)
            if len(parts) != 3:
                print("Usage: /addHost <ip:port> <fingerprint>")
                return
            ip_port, fingerprint = parts[1], parts[2]
            try:
                add_host(ip_port, fingerprint)
            except Exception as e:
                print(f"Error adding host: {e}")
        
        elif command.startswith("/removehost "):
            parts = command.split(" ", 1)
            if len(parts) != 2:
                print("Usage: /removehost <ip:port>")
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
                print("Not connected. Use /connect <ip> <port> to connect to a peer.")
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

                # Bonus : STUN
                info = get_public_ip_and_port()
                if info:
                    print(f"STUN Public IP : {info['public_ip']}")
                    print(f"STUN Public Port : {info['public_port']}")
                    print(f"NAT Type : {info['nat_type']}")


        else:
            print(f"Unknown command. Type /help for a list of commands.")