"""
Main entry point for the Cigarettes P2P chat application.
Handles application startup, Tor initialization, and UI launch.
"""

import sys
from colorama import Fore, Style

from .ui.console_ui import ConsoleUI
from .network.tor_manager import launch_tor_with_hidden_service


def print_banner():
    """Display the application banner."""
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


def validate_port(port_str: str) -> int:
    """
    Validate and return port number.
    
    Args:
        port_str: Port string to validate
        
    Returns:
        Valid port number
        
    Raises:
        ValueError: If port is invalid
    """
    try:
        port = int(port_str)
        if not (1024 <= port <= 65535):
            raise ValueError("The port must be between 1024 and 65535.")
        return port
    except ValueError as e:
        raise ValueError(f"Invalid port: {str(e)}")


def main():
    """Main application entry point."""
    if len(sys.argv) != 1:
        print("Usage: python main.py <port (optional, default : 34567)>")
        print("Example: python main.py 34567")
        return

    try:
        # Default port
        port = 34567
        
        # Parse command line arguments if provided
        if len(sys.argv) > 1:
            port = validate_port(sys.argv[1])
            
    except ValueError as e:
        print(f"Error: {str(e)}")
        return

    # Display banner
    print_banner()
    
    # Launch Tor with hidden service
    try:
        proc, onion_addr = launch_tor_with_hidden_service(port)
        print(f"Your .onion address : {onion_addr}")
    except Exception as e:
        print(f"Failed to start Tor: {str(e)}")
        return

    # Start the console UI
    ui = ConsoleUI()
    try:
        ui.start(port)
    finally:
        print("Stopping Tor...")
        try:
            proc.terminate()
            proc.wait()
        except Exception as e:
            print(f"Error stopping Tor: {str(e)}")


if __name__ == "__main__":
    main() 