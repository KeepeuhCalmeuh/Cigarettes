from colorama import Fore, Style
from datetime import datetime
import os
from src.core import file_transfer

# All comments and docstrings below are translated to English.
# command handlers

def handle_connect_command(console_ui, parts):
    if len(parts) < 3:
        print("Usage: /connect <peer_onion_address> <PEER_FINGERPRINT> [port]")
        return
    onion_address = parts[1]
    fingerprint = parts[2]
    port = int(parts[3]) if len(parts) > 3 else 34567
    if console_ui.connection:
        console_ui.connection.connect_to_onion_peer(onion_address, fingerprint, port)

def handle_status_command(console_ui):
    if not console_ui.connection:
        print("No connection manager available.")
        return
    if console_ui.connection.connected:
        print("Status: Connected")
        try:
            peer_fingerprint = console_ui.connection.crypto.get_peer_fingerprint()
            nickname = console_ui.hosts_manager.get_nickname(peer_fingerprint)
            print(f"Peer: {nickname if nickname else peer_fingerprint[:8]}")
            print(f"Fingerprint: {peer_fingerprint}")
        except:
            print("Peer: Unknown")
    else:
        print("Status: Not connected")

def handle_stop_command(console_ui):
    if console_ui.connection and console_ui.connection.connected:
        try:
            console_ui.connection.send_message("__DISCONNECT__")
        except Exception:
            pass
        console_ui.connection.stop()
        print("Disconnected from peer.")
        print("Waiting for new connection...")
        console_ui._display_prompt()
    else:
        print("Not connected to any peer.")

def handle_save_command(console_ui):
    if not console_ui.history:
        print("No conversation history to save.")
        return
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    history_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "history")
    os.makedirs(history_dir, exist_ok=True)
    filename = os.path.join(history_dir, f"conversation_{timestamp}.txt")
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("Conversation History\n")
            f.write("===================\n\n")
            for entry in console_ui.history:
                f.write(f"{entry}\n")
        print(f"Conversation saved to: {filename}")
        console_ui.connection.send_message(Fore.LIGHTYELLOW_EX + "[INFO] Peer has saved the conversation." + Style.RESET_ALL)
    except Exception as e:
        print(f"Error saving conversation: {str(e)}")

def handle_ping_command(console_ui):
    if not console_ui.connection or not console_ui.connection.connected:
        print("Not connected to any peer.")
        return
    print("Pinging peer...")
    response_time = console_ui.connection.ping_peer()*1000
    if response_time is not None:
        print(Fore.LIGHTBLUE_EX + f"Ping response time: {response_time:.3f} ms" + Style.RESET_ALL)
    else:
        print("Ping failed or timed out.")

def handle_info_command(console_ui):
    if not console_ui.connection:
        print("No connection manager available.")
        return
    try:
        fingerprint = console_ui.connection.crypto.get_public_key_fingerprint()
        print(f"Your fingerprint: {fingerprint}")
        print(f"Listening port: {console_ui.connection.listen_port}")
        if console_ui.connection.connected:
            try:
                peer_fingerprint = console_ui.connection.crypto.get_peer_fingerprint()
                nickname = console_ui.hosts_manager.get_nickname(peer_fingerprint)
                print(f"Connected to: {nickname if nickname else peer_fingerprint[:8]}")
            except:
                print("Connected to: Unknown peer")
        else:
            print("Not connected to any peer.")
    except Exception as e:
        print(f"Error getting info: {str(e)}")

def handle_rename_command(console_ui, parts):
    if len(parts) != 3:
        print("Usage: /rename <fingerprint> <new_name>")
        return
    fingerprint = parts[1]
    new_name = parts[2]
    console_ui.hosts_manager.set_nickname(fingerprint, new_name)
    print(f"Nickname updated for {fingerprint}")

def handle_addhost_command(console_ui, parts):
    if len(parts) != 3:
        print("Usage: /addHost <peer_onion_address> <fingerprint>")
        return
    address = parts[1]
    fingerprint = parts[2]
    console_ui.hosts_manager.add_host(address, fingerprint)

def handle_removehost_command(console_ui, parts):
    if len(parts) != 2:
        print("Usage: /removehost <peer_onion_address>")
        return
    address = parts[1]
    console_ui.hosts_manager.remove_host(address)

def handle_listhosts_command(console_ui):
    console_ui.hosts_manager.list_known_hosts()

def handle_multiline_command(console_ui):
    console_ui._multiline_mode = True
    print("Multi-line mode activated. Type your message:")

def handle_exit_command(console_ui):
    print("Exiting...")
    console_ui._stop_flag.set()
    if console_ui.connection and console_ui.connection.connected:
        try:
            console_ui.connection.send_message("__DISCONNECT__")
        except Exception:
            pass
    if console_ui.connection:
        console_ui.connection.stop()

def handle_send_file_command(console_ui, parts):
    if len(parts) != 2:
        print("Usage: /send_file <file_path>")
        return
    file_path = parts[1]
    msg = file_transfer.initiate_file_transfer(file_path)
    if not msg:
        print(Fore.LIGHTRED_EX + "[ERROR] File not found or cannot be read." + Style.RESET_ALL)
        return
    print(Fore.LIGHTYELLOW_EX + f"> [INFO] Preparing to send file: {file_path}" + Style.RESET_ALL)
    console_ui.connection.send_message(msg)
    print(Fore.LIGHTYELLOW_EX + "> [INFO] File transfer request sent. Waiting for acceptance..." + Style.RESET_ALL)


def handle_file_accept_command(console_ui, parts):
    if not file_transfer.FILE_TRANSFER_BOOL:
        print(Fore.LIGHTRED_EX + "> [INFO] No file transfer to accept." + Style.RESET_ALL)
        return
    msg = file_transfer.accept_file_transfer()
    console_ui.connection.send_message(msg)
    # Activate file receiving mode immediately
    console_ui.connection.activate_file_receiving_mode()
    # print("ON MET LE MODE RECEPTION DE FICHIER A TRUE DANS LE FICHIER CONNECTION_MESSAGE.PY et le _receiving_file est 2", console_ui.connection._receiving_file)
    print(Fore.LIGHTYELLOW_EX + "> [INFO] File transfer accepted. Waiting for file..." + Style.RESET_ALL)


def handle_file_decline_command(console_ui, parts):
    if not file_transfer.FILE_TRANSFER_BOOL:
        print(Fore.LIGHTRED_EX + "> [INFO] No file transfer to decline." + Style.RESET_ALL)
        return
    print(file_transfer.decline_file_transfer())
    console_ui.connection.send_message("__FILE_TRANSFER_DECLINED__")
    # Reset file transfer state on both sender and receiver sides
    file_transfer.reset_all_file_transfer_state()
    print(Fore.LIGHTRED_EX + "> [INFO] File transfer declined." + Style.RESET_ALL) 
    print(Fore.LIGHTYELLOW_EX + "[BUG TO FIX] [The next message received will be bugged and not displayed, the second message will be displayed as normal]" + Style.RESET_ALL)