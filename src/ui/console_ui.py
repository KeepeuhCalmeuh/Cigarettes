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
import time
import ast
from src.core import file_transfer


try:
    import keyboard
    KEYBOARD_AVAILABLE = True
except ImportError:
    KEYBOARD_AVAILABLE = False

from ..network.connection import P2PConnection
from ..core.hosts import KnownHostsManager
from .command_handlers import (
    handle_connect_command,
    handle_status_command,
    handle_stop_command,
    handle_save_command,
    handle_ping_command,
    handle_info_command,
    handle_rename_command,
    handle_addhost_command,
    handle_removehost_command,
    handle_listhosts_command,
    handle_multiline_command,
    handle_exit_command,
    handle_send_file_command,
    handle_file_accept_command,
    handle_file_decline_command
)


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
        
        # Détection message de demande de transfert de fichier
        info_msg = file_transfer.handle_file_transfer_request(message)
        if info_msg:
            print(f"> {info_msg}")
            self._display_prompt()
            return

        # Détection acceptation transfert côté émetteur
        if file_transfer.FILE_TRANSFER_PROCEDURE and message.startswith("__FILE_TRANSFER_ACCEPTED__"):
            print("> [INFO] File transfer accepted by peer. Sending file...")
            chunks = file_transfer.handle_file_transfer_accepted()
            for idx, chunk in enumerate(chunks):
                self.connection.send_message(chunk)
                print(f"> [INFO] Sending chunk {idx+1}/{len(chunks)}", end='\r')
            print("> [INFO] File sent successfully!")
            self._display_prompt()
            return

        # Réception de chunk de fichier (à adapter selon protocole réel)
        if file_transfer.FILE_TRANSFER_BOOL and isinstance(message, bytes):
            done = file_transfer.receive_file_chunk(message)
            # Affichage barre de progression ASCII (à améliorer)
            percent = file_transfer.file_receive_context['received_size'] / file_transfer.file_receive_context['file_size'] * 100
            print(f"> [INFO] Receiving file... {percent:.1f}%", end='\r')
            if done:
                file_transfer.reset_file_receive_context()
                print(f"\n> [INFO] File received successfully and saved to received_files/")
            self._display_prompt()
            return

        # Gestion de la déconnexion du pair
        if message.strip() == "__DISCONNECT__":
            print(Fore.LIGHTYELLOW_EX + "[INFO] The peer has disconnected." + Style.RESET_ALL)
            if self.connection:
                self.connection.stop()  # Ne ferme que la connexion pair-à-pair
            print("Waiting for new connection...")
            self.display_help()
            self._display_prompt()
            return

        # Handle multi-line received messages
        if '\n' in message:
            print("\n\r")
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
        print(Fore.LIGHTCYAN_EX + f"Listening on port {port}" + Style.RESET_ALL)
        print(Fore.LIGHTCYAN_EX + f"Your fingerprint: {self.connection.crypto.get_public_key_fingerprint()}" + Style.RESET_ALL)
        
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
            print(f"[ You | {datetime.now().strftime('%H:%M:%S')} ] {message}")
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
                handle_connect_command(self, parts)
            elif cmd == '/status':
                handle_status_command(self)
            elif cmd == '/stop':
                handle_stop_command(self)
            elif cmd == '/save':
                handle_save_command(self)
            elif cmd == '/ping':
                handle_ping_command(self)
            elif cmd == '/info':
                handle_info_command(self)
            elif cmd == '/rename':
                handle_rename_command(self, parts)
            elif cmd == '/addhost':
                handle_addhost_command(self, parts)
            elif cmd == '/removehost':
                handle_removehost_command(self, parts)
            elif cmd == '/listhosts':
                handle_listhosts_command(self)
            elif cmd == '/multiline':
                handle_multiline_command(self)
            elif cmd == '/help':
                self.display_help()
            elif cmd == '/exit':
                handle_exit_command(self)
            elif cmd == '/send_file':
                handle_send_file_command(self, parts)
            elif cmd == '/__file_accept__':
                handle_file_accept_command(self, parts)
            elif cmd == '/__file_decline__':
                handle_file_decline_command(self, parts)
            else:
                print(f"Unknown command: {cmd}")
                print("Type /help for available commands.")
                
        except Exception as e:
            print(f"Error executing command: {str(e)}")
        
        # Display prompt after command execution
        self._display_prompt()

    def stop(self) -> None:
        """Stop the UI and cleanup."""
        self._stop_flag.set()
        if self.connection:
            self.connection.stop() 