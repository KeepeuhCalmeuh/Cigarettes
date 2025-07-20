"""
Console user interface for the P2P chat application.
Handles user input, command processing, and message display.
"""

import threading
import sys
from typing import Optional, List
from datetime import datetime
import os
from colorama import Fore, Style

try:
    import keyboard
    KEYBOARD_AVAILABLE = True
except ImportError:
    KEYBOARD_AVAILABLE = False

from ..network.connection import P2PConnection
from ..core.hosts import KnownHostsManager


class ConsoleUI:
    """
    Console user interface for managing P2P connections and chat interactions.
    """
    
    def __init__(self):
        """Initialize the console UI."""
        self.connection: Optional[P2PConnection] = None
        self.hosts_manager = KnownHostsManager()
        self._stop_flag = threading.Event()
        self.history: List[str] = []
        self._multiline_mode = False
        self._current_message: List[str] = []
        self._pending_file = None

    def display_help(self) -> None:
        """Display help for available commands."""
        print("\nAvailable Commands :")
        print("  /connect <peer_onion_address> <PEER_FINGERPRINT> <peer_listening_port (optional, default : 34567)> - Connect to a remote peer")
        print("  /status                                    - Display connection status and peer information")
        print("  /stop                                      - Disconnect from the peer without exiting the application")
        print("  /save                                      - Save the discussion history to a .txt file")
        print("  /ping                                      - Ping the connected peer and display response time")
        print("  /info                                      - Displays your fingerprint, .onion address and listening port")
        print("  /rename <fingerprint> <new_name>           - Rename a peer in known hosts")
        print("  /addHost <peer_onion_address> <fingerprint> - Add a host to known hosts")
        print("  /removehost <peer_onion_address>            - Remove a host from known hosts")
        print("  /listHosts                                 - List all known hosts")
        print("  /multiline                                 - Toggle multi-line message mode (use Shift+Enter for new line, Enter to send, CANCEL to cancel)")
        print("  /help                                      - Displays this help")
        print("  /exit                                      - Exit the application")

        print("\nTo send a message, simply type it and press Enter.")
        print("Waiting for connection on the specified port...\n")

    def handle_message(self, message: str) -> None:
        """
        Callback to display received messages with timestamp and save in history.
        Also handles file transfer protocol.
        """
        now = datetime.now().strftime("%H:%M:%S")
        
        # File transfer protocol handling
        if self._pending_file and self._pending_file.get('status') == 'waiting':
            # Handle peer response to file request
            if message.startswith("__FILE_ACCEPT__"):
                print(Fore.LIGHTGREEN_EX + f"[INFO] Peer accepted file transfer. Sending file..." + Style.RESET_ALL)
                self._pending_file['status'] = 'sending'
                self.connection.send_file_data(self._pending_file['file_path'], 
                                            callback=lambda p: print(Fore.LIGHTCYAN_EX + f"[INFO] Sending progress: {p*100:.1f}%" + Style.RESET_ALL, end='\r'))
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
                path = self.connection.receive_file(file_name, file_size, save_dir="received_files", 
                                                 callback=lambda p: print(Fore.LIGHTCYAN_EX + f"[INFO] Receiving progress: {p*100:.1f}%" + Style.RESET_ALL, end='\r'))
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

    def _display_prompt(self) -> None:
        """Display the appropriate prompt based on mode."""
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
                    break
                    
                lines.append(line)
                
        except KeyboardInterrupt:
            print("\nMulti-line input cancelled.")
            return ""
        
        message = '\n'.join(lines)
        print("---")
        return message

    def start(self, port: int) -> None:
        """
        Start the console UI and begin listening for connections.
        
        Args:
            port: Port to listen for connections
        """
        self.connection = P2PConnection(port, self.handle_message)
        self.connection.start_server()
        
        # Display startup information
        print(f"Listening on port {port}")
        print(f"Your fingerprint: {self.connection.crypto.get_public_key_fingerprint()}")
        
        self.display_help()
        self._display_prompt()
        self._input_loop()

    def _input_loop(self) -> None:
        """Main input loop for processing user commands and messages."""
        while not self._stop_flag.is_set():
            try:
                if self._multiline_mode:
                    message = self._get_multiline_input_advanced() if KEYBOARD_AVAILABLE else self._get_multiline_input_simple()
                    if message:
                        self._send_message(message)
                    self._multiline_mode = False
                else:
                    user_input = input().strip()
                    if user_input.startswith('/'):
                        self._handle_command(user_input)
                    elif user_input:
                        self._send_message(user_input)
                        
            except KeyboardInterrupt:
                print("\nExiting...")
                break
            except EOFError:
                print("\nExiting...")
                break

    def _send_message(self, message: str) -> None:
        """
        Send a message to the connected peer.
        
        Args:
            message: Message to send
        """
        if not self.connection or not self.connection.connected:
            print("Not connected to any peer.")
            self._display_prompt()
            return
            
        try:
            self.connection.send_message(message)
        except Exception as e:
            print(f"Error sending message: {str(e)}")
        
        # Display prompt after sending message
        self._display_prompt()

    def _handle_command(self, command: str) -> None:
        """
        Handle user commands.
        
        Args:
            command: Command string to process
        """
        parts = command.split()
        cmd = parts[0].lower()
        
        try:
            if cmd == '/connect':
                self._handle_connect_command(parts)
            elif cmd == '/status':
                self._handle_status_command()
            elif cmd == '/stop':
                self._handle_stop_command()
            elif cmd == '/save':
                self._handle_save_command()
            elif cmd == '/ping':
                self._handle_ping_command()
            elif cmd == '/info':
                self._handle_info_command()
            elif cmd == '/rename':
                self._handle_rename_command(parts)
            elif cmd == '/addhost':
                self._handle_addhost_command(parts)
            elif cmd == '/removehost':
                self._handle_removehost_command(parts)
            elif cmd == '/listhosts':
                self._handle_listhosts_command()
            elif cmd == '/multiline':
                self._handle_multiline_command()
            elif cmd == '/help':
                self.display_help()
            elif cmd == '/exit':
                self._handle_exit_command()
            else:
                print(f"Unknown command: {cmd}")
                print("Type /help for available commands.")
                
        except Exception as e:
            print(f"Error executing command: {str(e)}")
        
        # Display prompt after command execution
        self._display_prompt()

    def _handle_connect_command(self, parts: List[str]) -> None:
        """Handle /connect command."""
        if len(parts) < 3:
            print("Usage: /connect <peer_onion_address> <PEER_FINGERPRINT> [port]")
            return
            
        onion_address = parts[1]
        fingerprint = parts[2]
        port = int(parts[3]) if len(parts) > 3 else 34567
        
        if self.connection:
            self.connection.connect_to_onion_peer(onion_address, fingerprint, port)

    def _handle_status_command(self) -> None:
        """Handle /status command."""
        if not self.connection:
            print("No connection manager available.")
            return
            
        if self.connection.connected:
            print("Status: Connected")
            try:
                peer_fingerprint = self.connection.crypto.get_peer_fingerprint()
                nickname = self.hosts_manager.get_nickname(peer_fingerprint)
                print(f"Peer: {nickname if nickname else peer_fingerprint[:8]}")
                print(f"Fingerprint: {peer_fingerprint}")
            except:
                print("Peer: Unknown")
        else:
            print("Status: Not connected")

    def _handle_stop_command(self) -> None:
        """Handle /stop command."""
        if self.connection and self.connection.connected:
            self.connection.stop()
            print("Disconnected from peer.")
        else:
            print("Not connected to any peer.")

    def _handle_save_command(self) -> None:
        """Handle /save command."""
        if not self.history:
            print("No conversation history to save.")
            return
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"conversation_{timestamp}.txt"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("Conversation History\n")
                f.write("===================\n\n")
                for entry in self.history:
                    f.write(f"{entry}\n")
            print(f"Conversation saved to: {filename}")
        except Exception as e:
            print(f"Error saving conversation: {str(e)}")

    def _handle_ping_command(self) -> None:
        """Handle /ping command."""
        if not self.connection or not self.connection.connected:
            print("Not connected to any peer.")
            return
            
        print("Pinging peer...")
        response_time = self.connection.ping_peer()
        if response_time is not None:
            print(f"Ping response time: {response_time:.3f} seconds")
        else:
            print("Ping failed or timed out.")

    def _handle_info_command(self) -> None:
        """Handle /info command."""
        if not self.connection:
            print("No connection manager available.")
            return
            
        try:
            fingerprint = self.connection.crypto.get_public_key_fingerprint()
            print(f"Your fingerprint: {fingerprint}")
            print(f"Listening port: {self.connection.listen_port}")
            
            # Show connection status
            if self.connection.connected:
                try:
                    peer_fingerprint = self.connection.crypto.get_peer_fingerprint()
                    nickname = self.hosts_manager.get_nickname(peer_fingerprint)
                    print(f"Connected to: {nickname if nickname else peer_fingerprint[:8]}")
                except:
                    print("Connected to: Unknown peer")
            else:
                print("Not connected to any peer.")
                
        except Exception as e:
            print(f"Error getting info: {str(e)}")

    def _handle_rename_command(self, parts: List[str]) -> None:
        """Handle /rename command."""
        if len(parts) != 3:
            print("Usage: /rename <fingerprint> <new_name>")
            return
            
        fingerprint = parts[1]
        new_name = parts[2]
        self.hosts_manager.set_nickname(fingerprint, new_name)
        print(f"Nickname updated for {fingerprint}")

    def _handle_addhost_command(self, parts: List[str]) -> None:
        """Handle /addhost command."""
        if len(parts) != 3:
            print("Usage: /addHost <peer_onion_address> <fingerprint>")
            return
            
        address = parts[1]
        fingerprint = parts[2]
        self.hosts_manager.add_host(address, fingerprint)

    def _handle_removehost_command(self, parts: List[str]) -> None:
        """Handle /removehost command."""
        if len(parts) != 2:
            print("Usage: /removehost <peer_onion_address>")
            return
            
        address = parts[1]
        self.hosts_manager.remove_host(address)

    def _handle_listhosts_command(self) -> None:
        """Handle /listhosts command."""
        self.hosts_manager.list_known_hosts()

    def _handle_multiline_command(self) -> None:
        """Handle /multiline command."""
        self._multiline_mode = True
        print("Multi-line mode activated. Type your message:")

    def _handle_exit_command(self) -> None:
        """Handle /exit command."""
        print("Exiting...")
        self._stop_flag.set()
        if self.connection:
            self.connection.stop()

    def stop(self) -> None:
        """Stop the UI and cleanup."""
        self._stop_flag.set()
        if self.connection:
            self.connection.stop() 