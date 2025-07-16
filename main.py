import sys
from console_ui import ConsoleUI
from local_ip_utils import get_local_ip, get_public_ip_and_port
from colorama import Fore, Style


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
    if len(sys.argv) != 2:
        print("Usage: python main.py <port>")
        print("Exemple: python main.py 5000")
        return

    try:
        port = int(sys.argv[1])
        if not (1024 <= port <= 65535):
            raise ValueError("The port must be between 1024 and 65535.")
    except ValueError as e:
        print(f"Error: {str(e)}")
        return

    print_banner()
    print(f"Your local IP address : {get_local_ip()}")
    print(f"Your public IP address : {get_public_ip_and_port()['public_ip']}")
    print(f"Your public port : {get_public_ip_and_port()['public_port']}")
    print(f"Your NAT type : {get_public_ip_and_port()['nat_type']}")

    ui = ConsoleUI()
    ui.start(port)

if __name__ == "__main__":
    main()
