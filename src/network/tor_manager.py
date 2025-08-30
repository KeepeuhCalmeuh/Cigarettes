"""
Tor network management for onion routing and hidden services.
Handles Tor installation, configuration, and hidden service setup.
"""

import os
import sys
import platform
import subprocess
import requests
import shutil
import zipfile
import tarfile
import time
import tempfile
from typing import Tuple, Optional
import socket


class TorManager:
    """
    Manages Tor network integration including installation, configuration,
    and hidden service setup for anonymous communication.
    """
    
    TOR_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'tor')
    TOR_SOCKS_PORT = 9050
    TOR_VERSION = '14.5.4'
    
    # URL template for Tor Expert Bundle
    TOR_URL_TEMPLATE = (
        "https://archive.torproject.org/tor-package-archive/torbrowser/{version}/"
        "tor-expert-bundle-{os_arch_string}-{version}.tar.gz"
    )

    def __init__(self):
        """Initialize the Tor manager."""
        self.tor_binary = None
        self.tor_process = None

    def get_tor_url(self) -> str:
        """Build the correct Tor download URL based on OS and architecture."""
        os_name = platform.system()
        arch = platform.machine()
        
        # Normalize names to match Tor Project's URL format
        if os_name == 'Linux':
            os_str = 'linux'
            arch_str = 'x86_64'  # Tor doesn't support ARM as of July 2025
        elif os_name == 'Darwin':
            os_str = 'macos'
            arch_str = 'arm64' if 'arm' in arch else 'x86_64'
        elif os_name == 'Windows':
            os_str = 'windows'
            arch_str = 'x86_64'
        else:
            raise RuntimeError(f"Unsupported OS: {os_name}")
            
        os_arch_string = f"{os_str}-{arch_str}"
        
        url = self.TOR_URL_TEMPLATE.format(
            version=self.TOR_VERSION,
            os_arch_string=os_arch_string
        )
        print(f"Detected OS/Arch: {os_name}/{arch}. Using URL: {url}")
        return url

    def detect_os(self) -> str:
        """Detect OS and return key for Tor URLs."""
        os_name = platform.system()
        if os_name == 'Windows':
            return 'Windows'
        elif os_name == 'Linux':
            return 'Linux'
        elif os_name == 'Darwin':
            return 'Darwin'
        else:
            raise RuntimeError(f"Unsupported OS: {os_name}")

    def find_tor_binary(self) -> Optional[str]:
        """Search for Tor binary in the extracted directory."""
        possible_paths = [
            os.path.join(self.TOR_DIR, 'tor', 'tor'),
            os.path.join(self.TOR_DIR, 'Tor', 'tor'),
            os.path.join(self.TOR_DIR, 'tor', 'bin', 'tor'),
            os.path.join(self.TOR_DIR, 'bin', 'tor'),
            os.path.join(self.TOR_DIR, 'tor.exe'),
            os.path.join(self.TOR_DIR, 'tor')
        ]

        for path in possible_paths:
            if os.path.isfile(path):
                #print(f"Found Tor binary at: {path}")
                return path

        # List contents of TOR_DIR for debugging
        print("Failed to find TOR binary.\nDebug Info :")
        print(f"Contents of {self.TOR_DIR}:")
        if os.path.exists(self.TOR_DIR):
            for root, dirs, files in os.walk(self.TOR_DIR):
                level = root.replace(self.TOR_DIR, '').count(os.sep)
                indent = ' ' * 2 * level
                print(f"{indent}{os.path.basename(root)}/")
                subindent = ' ' * 2 * (level + 1)
                for file in files:
                    print(f"{subindent}{file}")

        return None

    def get_tor_binary_path(self) -> Optional[str]:
        """Return Tor binary path according to OS."""
        path = self.find_tor_binary()

        if not path:
            return None
        
        os_key = self.detect_os()
        if os_key in ['Linux', 'Darwin'] and os.path.isfile(path):
            try:
                os.chmod(path, 0o755)
                # print(f"Ensured {path} is executable.")
            except OSError as e:
                print(f"Warning: Could not set executable permission on {path}: {e}")
        
        return path

    def is_tor_present(self) -> bool:
        """Check if Tor binary is already present."""
        return self.get_tor_binary_path() is not None

    def download_tor(self) -> str:
        """Download Tor archive adapted to OS/Arch in a temporary folder."""
        url = self.get_tor_url()
        temp_dir = tempfile.mkdtemp()
        local_archive = os.path.join(temp_dir, os.path.basename(url))

        os.makedirs(self.TOR_DIR, exist_ok=True)
        print(f"Downloading Tor from {url} to {temp_dir}...")
        try:
            with requests.get(url, stream=True) as r:
                r.raise_for_status()
                with open(local_archive, 'wb') as f:
                    shutil.copyfileobj(r.raw, f)
            print(f"Archive downloaded: {local_archive}")
            return local_archive
        except requests.exceptions.RequestException as e:
            shutil.rmtree(temp_dir)
            raise RuntimeError(f"Failed to download Tor: {e}")

    def extract_tor(self, archive_path: str) -> None:
        """Extract Tor archive into the tor/ folder and clean up the archive."""
        temp_dir = os.path.dirname(archive_path)
        print(f"Extracting {archive_path} to {self.TOR_DIR}...")
        try:
            if archive_path.endswith('.zip'):
                with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                    zip_ref.extractall(self.TOR_DIR)
            elif archive_path.endswith('.tar.xz') or archive_path.endswith('.tar.gz'):
                mode = 'r:xz' if archive_path.endswith('.tar.xz') else 'r:gz'
                with tarfile.open(archive_path, mode) as tar_ref:
                    for member in tar_ref.getmembers():
                        # Remove the top-level directory from the path
                        member_path = member.name.split('/', 1)
                        if len(member_path) > 1 and member_path[1]:
                            member.name = member_path[1]
                            tar_ref.extract(member, self.TOR_DIR)
            print("Extraction completed.")
        except Exception as e:
            print(f"An error occurred during extraction: {e}")
            raise
        finally:
            # Clean up the temporary directory and the archive within it
            print(f"Cleaning up temporary directory: {temp_dir}")
            shutil.rmtree(temp_dir)

    def ensure_tor(self) -> None:
        """Check Tor presence, download and install if needed."""
        if self.is_tor_present():
            #print("Tor already present.")
            return
        
        print("Tor not found, starting download and install...")
        archive = self.download_tor()
        self.extract_tor(archive)
        
        if not self.is_tor_present():
            raise RuntimeError("Tor not found after installation!")
        else:
            print("Tor ready to use.")

    def launch_tor(self, extra_args: Optional[list] = None) -> subprocess.Popen:
        """Launch Tor as subprocess. Returns process handle."""
        tor_path = self.get_tor_binary_path()
        if not tor_path:
            raise RuntimeError(f"Tor binary not found: {tor_path}")

        # Prepare command
        cmd = [tor_path]
        if extra_args:
            cmd.extend(extra_args)
        
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            time.sleep(2)
            if process.poll() is not None: 
                out, err = process.communicate()
                print(f'Tor stdout: {out}')
                print(f'Tor stderr: {err}')
                if "error while loading shared libraries" in err:
                    missing_lib = None
                    for line in err.splitlines():
                        if "error while loading shared libraries" in line:
                            parts = line.split(":")
                            if len(parts) > 1:
                                missing_lib = parts[1].strip().split()[0]
                    if missing_lib:
                        print("\n[!] missing library:", missing_lib)
                        if sys.platform.startswith("linux"):
                            print(f"To fix, run:\n  sudo apt update && sudo apt install {missing_lib.split('.')[0]}")
                        else:
                            print("Please install the missing library via your package manager.")
                        raise RuntimeError(f"Tor cannot start because the following library is missing: {missing_lib}")
            return process
        except Exception as e:
            raise RuntimeError(f"Failed to launch Tor: {e}")

    def wait_for_tor_ready(self, timeout: int = 60) -> bool:
        """Wait for Tor to be ready (SOCKS5 proxy up)."""
        print("Waiting for Tor to be ready...")
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                # Try to connect to SOCKS5 proxy
                test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                test_socket.settimeout(2)
                test_socket.connect(('127.0.0.1', self.TOR_SOCKS_PORT))
                test_socket.close()
                print("Tor is ready!")
                return True
            except:
                time.sleep(1)
        
        print("Timeout waiting for Tor to be ready.")
        return False

    def get_project_root(self) -> str:
        """Retourne le chemin absolu de la racine du projet (là où se trouve le dossier 'tor')."""
        return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    def create_hidden_service_dir(self, port: int, base_dir: Optional[str] = None) -> str:
        """Create hidden service directory and configuration."""
        # Toujours utiliser la racine du projet comme base_dir
        if base_dir is None:
            base_dir = self.get_project_root()
        hidden_service_dir = os.path.join(base_dir, 'tor', 'hidden_service')
        os.makedirs(hidden_service_dir, exist_ok=True)
        os.chmod(hidden_service_dir, 0o700)
        # Crée aussi le dossier data avec permissions 700
        data_dir = os.path.join(base_dir, 'tor', 'data')
        os.makedirs(data_dir, exist_ok=True)
        os.chmod(data_dir, 0o700)
        # Create torrc configuration
        torrc_path = os.path.join(base_dir, 'tor', 'torrc')
        with open(torrc_path, 'w') as f:
            f.write(f"SocksPort {self.TOR_SOCKS_PORT}\n")
            f.write(f"HiddenServiceDir {hidden_service_dir}\n")
            f.write(f"HiddenServicePort {port} 127.0.0.1:{port}\n")
            f.write("DataDirectory " + os.path.join(base_dir, 'tor', 'data') + "\n")
            f.write("PidFile " + os.path.join(base_dir, 'tor', 'tor.pid') + "\n")
        return hidden_service_dir

    def launch_tor_with_hidden_service(self, port: int, base_dir: Optional[str] = None) -> Tuple[subprocess.Popen, str]:
        """
        Launch Tor with hidden service configuration.
        """
        # Ensure Tor is available
        self.ensure_tor()
        # Toujours utiliser la racine du projet comme base_dir
        if base_dir is None:
            base_dir = self.get_project_root()
        # Create hidden service directory
        hidden_service_dir = self.create_hidden_service_dir(port, base_dir)
        # Launch Tor
        torrc_path = os.path.join(base_dir, 'tor', 'torrc')
        extra_args = ['-f', torrc_path]
        self.tor_process = self.launch_tor(extra_args)
        # Wait for Tor to be ready
        if not self.wait_for_tor_ready():
            raise RuntimeError("Tor failed to start properly")
        # Read onion address
        hostname_file = os.path.join(hidden_service_dir, 'hostname')
        onion_address = None
        # Wait for hostname file to be created
        timeout = 30
        start_time = time.time()
        while time.time() - start_time < timeout:
            if os.path.exists(hostname_file):
                with open(hostname_file, 'r') as f:
                    onion_address = f.read().strip()
                break
            time.sleep(1)
        if not onion_address:
            raise RuntimeError("Failed to get onion address from Tor")
        return self.tor_process, onion_address

    def stop_tor(self) -> None:
        """Stop the Tor process."""
        if self.tor_process:
            try:
                self.tor_process.terminate()
                self.tor_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.tor_process.kill()
            except Exception as e:
                print(f"Error stopping Tor: {e}")
            finally:
                self.tor_process = None


# Global instance for backward compatibility
tor_manager = TorManager()


def launch_tor_with_hidden_service(port: int, base_dir: Optional[str] = None) -> Tuple[subprocess.Popen, str]:
    """
    Convenience function for backward compatibility.
    
    Args:
        port: Port for the hidden service
        base_dir: Base directory for Tor files
        
    Returns:
        Tuple of (Tor process, onion address)
    """
    return tor_manager.launch_tor_with_hidden_service(port, base_dir)