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

# =============================
# Embedded Tor Management Module
# =============================
# This module:
# 1. Detects OS and architecture
# 2. Checks for Tor presence in ./tor/
# 3. Downloads Tor if needed
# 4. Extracts/installs Tor
# 5. Launches Tor as subprocess
# 6. Verifies Tor is ready (SOCKS5 up)
# =============================

TOR_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tor')
TOR_BINARY = None  # Sera défini selon l'OS
TOR_SOCKS_PORT = 9050  # Port SOCKS5 par défaut

# Official Tor Expert Bundle URLs (updated 2025-06)
TOR_VERSION = '14.5.4'

# URL template allows for dynamic OS and architecture
TOR_URL_TEMPLATE = (
    "https://archive.torproject.org/tor-package-archive/torbrowser/{version}/"
    "tor-expert-bundle-{os_arch_string}-{version}.tar.gz"
)

def get_tor_url():
    """Builds the correct Tor download URL based on OS and architecture."""
    os_name = platform.system()
    arch = platform.machine()
    
    # Normalize names to match Tor Project's URL format
    if os_name == 'Linux':
        os_str = 'linux'
        # arch_str = 'aarch64' if 'aarch64' in arch or 'arm64' in arch else 'x86_64' future proofing it as Tor doesn't support arm as of July 2025
    elif os_name == 'Darwin':
        os_str = 'macos'
        arch_str = 'arm64' if 'arm' in arch else 'x86_64'
    elif os_name == 'Windows':
        os_str = 'windows'
        arch_str = 'x86_64'
    else:
        raise RuntimeError(f"Unsupported OS: {os_name}")
        
    os_arch_string = f"{os_str}-{arch_str}"
    
    url = TOR_URL_TEMPLATE.format(
        version=TOR_VERSION,
        os_arch_string=os_arch_string
    )
    print(f"Detected OS/Arch: {os_name}/{arch}. Using URL: {url}")
    return url



def detect_os():
    """Detects OS and returns key for TOR_URLS."""
    os_name = platform.system()
    if os_name == 'Windows':
        return 'Windows'
    elif os_name == 'Linux':
        return 'Linux'
    elif os_name == 'Darwin':
        return 'Darwin'
    else:
        raise RuntimeError(f"Unsupported OS: {os_name}")


def find_tor_binary():
    """Searches for Tor binary in the extracted directory."""
    possible_paths = [
        os.path.join(TOR_DIR, 'tor', 'tor'),
        os.path.join(TOR_DIR, 'Tor', 'tor'),
        os.path.join(TOR_DIR, 'tor', 'bin', 'tor'),
        os.path.join(TOR_DIR, 'bin', 'tor'),
        os.path.join(TOR_DIR, 'tor.exe'),
        os.path.join(TOR_DIR, 'tor')
    ]

    for path in possible_paths:
        if os.path.isfile(path):
            print(f"Found Tor binary at: {path}")
            return path

    # List contents of TOR_DIR for debugging
    print(f"Contents of {TOR_DIR}:")
    if os.path.exists(TOR_DIR):
        for root, dirs, files in os.walk(TOR_DIR):
            level = root.replace(TOR_DIR, '').count(os.sep)
            indent = ' ' * 2 * level
            print(f"{indent}{os.path.basename(root)}/")
            subindent = ' ' * 2 * (level + 1)
            for file in files:
                print(f"{subindent}{file}")

    return None


def get_tor_binary_path():
    """Returns Tor binary path according to OS."""
    os_key = detect_os()
    path= find_tor_binary()

    if not path : 
        return None
    
    if os_key in ['Linux','Darwin'] and os.path.isfile(path):
        try :
            os.chmod(path, 0o755)
            print(f"Ensured {path} is executable.")
        except OSError as e:
            print(f"Warning: Could not set executable permission on {path}: {e}")
    
    return path




def is_tor_present():
    """Checks if Tor binary is already present."""
    return get_tor_binary_path() is not None

def download_tor():
    """Downloads Tor archive adapted to OS/Arch in a temporary folder."""
    url = get_tor_url() # Get the dynamically generated URL
    temp_dir = tempfile.mkdtemp()
    local_archive = os.path.join(temp_dir, os.path.basename(url))

    os.makedirs(TOR_DIR, exist_ok=True)
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


def extract_tor(archive_path):
    """Extracts Tor archive into the tor/ folder and cleans up the archive."""
    temp_dir = os.path.dirname(archive_path)
    print(f"Extracting {archive_path} to {TOR_DIR}...")
    try:
        if archive_path.endswith('.zip'):
            with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                zip_ref.extractall(TOR_DIR)
        elif archive_path.endswith('.tar.xz') or archive_path.endswith('.tar.gz'):
            mode = 'r:xz' if archive_path.endswith('.tar.xz') else 'r:gz'
            with tarfile.open(archive_path, mode) as tar_ref:
                for member in tar_ref.getmembers():
                    # Remove the top-level directory from the path
                    member_path = member.name.split('/', 1)
                    if len(member_path) > 1 and member_path[1]:
                        member.name = member_path[1]
                        tar_ref.extract(member, TOR_DIR)
        print("Extraction completed.")
    except Exception as e:
        print(f"An error occurred during extraction: {e}")
        raise # Re-raise the exception to be caught by the caller
    finally:
        # Clean up the temporary directory and the archive within it
        print(f"Cleaning up temporary directory: {temp_dir}")
        shutil.rmtree(temp_dir)


def ensure_tor():
    """Checks Tor presence, downloads and installs if needed."""
    if is_tor_present():
        print("Tor already present.")
        return
    
    print("Tor not found, starting download and install...")
    archive = download_tor()
    extract_tor(archive)
    # Optional: remove archive after extraction
    # os.remove(archive)
    if not is_tor_present():
        raise RuntimeError("Tor not found after installation!")
    else  : print("Tor ready to use.")


def launch_tor(extra_args=None):
    """Launches Tor as subprocess. Returns process handle."""
    tor_path = get_tor_binary_path()
    if not tor_path:
        raise RuntimeError(f"Tor binary not found: {tor_path}")
    
    args = [tor_path]
    if extra_args:
        args.extend(extra_args)
    print(f"Launching Tor: {' '.join(args)}")
    proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return proc


def wait_for_tor_ready(timeout=60):
    """Waits for Tor SOCKS5 port to be open (ready)."""
    import socket
    print(f"Waiting for Tor SOCKS5 proxy on 127.0.0.1:{TOR_SOCKS_PORT}...")
    start = time.time()
    while time.time() - start < timeout:
        try:
            with socket.create_connection(('127.0.0.1', TOR_SOCKS_PORT), timeout=2):
                print("Tor SOCKS5 ready!")
                return True
        except (socket.timeout, ConnectionRefusedError):
            time.sleep(1)
    raise TimeoutError("Tor did not start within the timeout period.")


# =============================
# Tor Hidden Service Management
# =============================

def create_hidden_service_dir(port, base_dir=None):
    """
    Crée un dossier fixe pour le Hidden Service afin de conserver la même adresse .onion.
    """
    if base_dir is None:
        base_dir = os.path.join(TOR_DIR, 'hidden_service')
    os.makedirs(base_dir, exist_ok=True)

    # Utiliser un dossier fixe pour le service
    hs_dir = os.path.join(base_dir, 'my_service')
    os.makedirs(hs_dir, exist_ok=True)

    torrc_path = os.path.join(base_dir, 'torrc')
    with open(torrc_path, 'w') as f:
        f.write(f"SocksPort {TOR_SOCKS_PORT}\n")
        f.write(f"DataDirectory {os.path.join(hs_dir, 'data')}\n")
        f.write(f"HiddenServiceDir {hs_dir}\n")
        f.write(f"HiddenServicePort {port} 127.0.0.1:{port}\n")

    return hs_dir, torrc_path


def launch_tor_with_hidden_service(port, base_dir=None):
    """
    Launches Tor with a Hidden Service exposing the given local port.
    Returns Tor process and generated .onion address.
    """

    hs_dir, torrc_path = create_hidden_service_dir(port, base_dir)
    tor_path = get_tor_binary_path()
    if not tor_path : 
        raise RuntimeError("Cannot launch Tor, binary not found.")
    args = [tor_path, '-f', torrc_path]
    print(f"Launching Tor with Hidden Service: {' '.join(args)}")
    proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # Wait for hostname file creation (.onion address)
    hostname_path = os.path.join(hs_dir, 'hostname')
    print("Waiting for .onion address creation...")

    start_time = time.time()
    while time.time() - start_time < 60:  # 60-second timeout
        if os.path.isfile(hostname_path) and os.path.getsize(hostname_path) > 0:
            with open(hostname_path, 'r') as f:
                onion_addr = f.read().strip()
            print(f".onion address generated: {onion_addr}")
            return proc, onion_addr
        time.sleep(1)

    """
    for _ in range(60):  # Timeout ~60s
        if os.path.isfile(hostname_path):
            with open(hostname_path, 'r') as f:
                onion_addr = f.read().strip()
            print(f".onion address generated: {onion_addr}")
            return proc, onion_addr
        time.sleep(1)"""
    
    proc.terminate()
    raise TimeoutError("Hidden Service was not created within timeout.")


if __name__ == "__main__":
    print("[TOR MANAGER] Initializing...")
    ensure_tor()
    
    print("\n--- Testing Tor Client ---")
    tor_process = None
    try:
        tor_process = launch_tor()
        wait_for_tor_ready()
        print("[SUCCESS] Tor client launched and ready.")
    except (RuntimeError, TimeoutError) as e:
        print(f"[ERROR] {e}")
    finally:
        if tor_process:
            print("Stopping Tor client...")
            tor_process.terminate()
            tor_process.wait()