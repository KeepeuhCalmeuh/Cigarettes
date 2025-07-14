import threading
import sys
from typing import Optional
from connection import P2PConnection
from datetime import datetime
from known_hosts_manager import get_nickname, set_nickname, add_host, list_known_hosts
import os


class ConsoleUI:
    def __init__(self):
        self.connection: Optional[P2PConnection] = None
        self._stop_flag = threading.Event()
        self.history = []  # Discussion history
        
    def display_help(self):
        """Displays help for available commands"""
        print("\nAvailable Commands :")
        print("  /connect <ip> <port>                       - Connect to a remote peer")
        print("  /stop                                      - Disconnect from the peer without exiting the application")
        print("  /save                                      - Save the discussion history to a .txt file")
        print("  /fingerprint                               - Displays the fingerprint of your public key")
        print("  /rename <fingerprint> <new_name>           - Rename a peer in known hosts")
        print("  /addHost <ip:port> <fingerprint>           - Add a host to known hosts")
        print("  /listHosts                                 - List all known hosts")

        print("  /help                                      - Displays this help")
        print("  /exit                                      - Exit the application")

        print("\nTo send a message, simply type it and press Enter.")
        print("Waiting for connection on the specified port...\n")

    def handle_message(self, message: str):
        """Callback to display received messages with timestamp and save in history"""
        now = datetime.now().strftime("%H:%M:%S")
        line = f"[{now}] {message}"
        self.history.append(line)
        print(f"\n{line}")
        sys.stdout.write("> ")
        sys.stdout.flush()

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
                user_input = input("> ").strip()
                
                if not user_input:
                    continue
                
                if user_input.startswith("/"):
                    self._handle_command(user_input)
                elif self.connection.connected:
                    now = datetime.now().strftime("%H:%M:%S")
                    line = f"[You | {now}] {user_input}"
                    print(line)
                    self.history.append(line)
                    self.connection.send_message(user_input)
                else:
                    print("Not connected. Use /connect <ip> <port> to connect to a peer.")
            
            except EOFError:
                break
            except Exception as e:
                print(f"Error: {str(e)}")

    def _handle_command(self, command: str):
        """Manages special orders"""
        parts = command.split()
        cmd = parts[0].lower()

        if cmd == "/help":
            self.display_help()

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
            if len(parts) != 3:
                print("Usage: /connect <ip> <port>")
                return

            try:
                ip = parts[1]
                port = int(parts[2])
                
                if self.connection.connected:
                    print("Already connected to a peer.")
                    return
                
                print(f"Attempting to connect to {ip}:{port}...")
                if self.connection.connect_to_peer(ip, port):
                    print("connected!")
                
            except ValueError:
                print("The port must be a number.")
            
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

        elif command.startswith("/rename "):
            parts = command.split(" ", 2)
            if len(parts) != 3:
                print("Usage: /rename <fingerprint> <new_name>")
                return
            fingerprint, new_name = parts[1], parts[2]
            try:
                set_nickname(fingerprint, new_name)
                print(f"Updated {fingerprint} peer name: {new_name}")
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

        else:
            print(f"Unknown command. Type /help for a list of commands.")