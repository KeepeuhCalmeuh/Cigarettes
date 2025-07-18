import sys
from console_ui import ConsoleUI
from colorama import Fore, Style
from tor_manager import launch_tor_with_hidden_service

def print_banner():
    banner = r"""
    


    
   █████████   ███                                         █████     █████
  ███░░░░░███ ░░░                                         ░░███     ░░███
 ███     ░░░  ████   ███████  ██████   ████████   ██████  ███████   ███████    ██████   █████
░███         ░░███  ███░░███ ░░░░░███ ░░███░░███ ███░░███░░░███░   ░░░███░    ███░░███ ███░░
░███          ░███ ░███ ░███  ███████  ░███ ░░░ ░███████   ░███      ░███    ░███████ ░░█████
░░███     ███ ░███ ░███ ░███ ███░░███  ░███     ░███░░░    ░███ ███  ░███ ███░███░░░   ░░░░███
 ░░█████████  █████░░███████░░████████ █████    ░░██████   ░░█████   ░░█████ ░░██████  ██████
  ░░░░░░░░░  ░░░░░  ░░░░░███ ░░░░░░░░ ░░░░░      ░░░░░░     ░░░░░     ░░░░░   ░░░░░░  ░░░░░░
                    ███ ░███
                   ░░██████
                    ░░░░░░
               P2P Encrypted Terminal Chat
               Project: Cigarettes
               Author : KeepeuhCalmeuh
    """
    print(Fore.RED + banner + Style.RESET_ALL)



def main():
    if len(sys.argv) != 1:
        print("Usage: python main.py <port (optional, default : 34567)>")
        print("Exemple: python main.py 34567")
        return

    try:
        if len(sys.argv) == 1:
            port = 34567
        else:
            port = int(sys.argv[1])
            if not (1024 <= port <= 65535):
                raise ValueError("The port must be between 1024 and 65535.")
    except ValueError as e:
        print(f"Error: {str(e)}")
        return

    print_banner()
    proc, onion_addr = launch_tor_with_hidden_service(port)
    print(f"Your .onion address : {onion_addr}")


    ui = ConsoleUI()
    try:
        ui.start(port)
    finally:
        print("Stopping Tor...")
        proc.terminate()
        proc.wait()

if __name__ == "__main__":
    main()
