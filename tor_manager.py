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

TOR_DIR = os.path.join(os.path.dirname(__file__), 'tor')
TOR_BINARY = None  # Sera défini selon l'OS
TOR_SOCKS_PORT = 9050  # Port SOCKS5 par défaut

# URLs officielles Tor Expert Bundle (à jour 2024-06)
TOR_VERSION = '0.4.8.12'
TOR_URLS = {
    'Windows': f'https://archive.torproject.org/tor-package-archive/torbrowser/14.5.4/tor-expert-bundle-windows-x86_64-14.5.4.tar.gz',
    'Linux': f'https://archive.torproject.org/tor-package-archive/torbrowser/14.5.4/tor-expert-bundle-linux-x86_64-14.5.4.tar.gz',
    'Darwin': f'https://archive.torproject.org/tor-package-archive/torbrowser/14.5.4/tor-expert-bundle-macos-x86_64-14.5.4.tar.gz',
}


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


def get_tor_binary_path():
    """Returns Tor binary path according to OS."""
    os_key = detect_os()
    if os_key == 'Windows':
        return os.path.join(TOR_DIR, 'Tor', 'tor.exe')
    elif os_key == 'Linux':
        return os.path.join(TOR_DIR, 'tor', 'tor')
    elif os_key == 'Darwin':
        return os.path.join(TOR_DIR, 'Tor', 'tor')


def is_tor_present():
    """Checks if Tor binary is already present."""
    return os.path.isfile(get_tor_binary_path())


def download_tor():
    """Downloads Tor archive adapted to OS in tor/ folder."""
    os_key = detect_os()
    url = TOR_URLS[os_key]
    local_archive = os.path.join(TOR_DIR, os.path.basename(url))
    os.makedirs(TOR_DIR, exist_ok=True)
    print(f"Downloading Tor from {url} ...")
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(local_archive, 'wb') as f:
            shutil.copyfileobj(r.raw, f)
    print(f"Archive downloaded: {local_archive}")
    return local_archive


def extract_tor(archive_path):
    """Extracts Tor archive in tor/ folder."""
    print(f"Extracting {archive_path} ...")
    if archive_path.endswith('.zip'):
        with zipfile.ZipFile(archive_path, 'r') as zip_ref:
            zip_ref.extractall(TOR_DIR)
    elif archive_path.endswith('.tar.xz') or archive_path.endswith('.tar.gz'):
        mode = 'r:xz' if archive_path.endswith('.tar.xz') else 'r:gz'
        with tarfile.open(archive_path, mode) as tar_ref:
            tar_ref.extractall(TOR_DIR)
    else:
        raise RuntimeError("Unsupported archive format")
    print("Extraction completed.")


def ensure_tor():
    """Checks Tor presence, downloads and installs if needed."""
    if is_tor_present():
        print("Tor already present.")
        return
    archive = download_tor()
    extract_tor(archive)
    # Optional: remove archive after extraction
    os.remove(archive)
    if not is_tor_present():
        raise RuntimeError("Tor not found after installation!")
    print("Tor ready to use.")


def launch_tor(extra_args=None):
    """Launches Tor as subprocess. Returns process handle."""
    tor_path = get_tor_binary_path()
    if not os.path.isfile(tor_path):
        raise RuntimeError(f"Tor binary not found: {tor_path}")
    args = [tor_path]
    if extra_args:
        args += extra_args
    print(f"Launching Tor: {' '.join(args)}")
    proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return proc


def wait_for_tor_ready(timeout=60):
    """Waits for Tor SOCKS5 port to be open (ready)."""
    import socket
    start = time.time()
    while time.time() - start < timeout:
        try:
            with socket.create_connection(('127.0.0.1', TOR_SOCKS_PORT), timeout=2):
                print("Tor SOCKS5 ready!")
                return True
        except Exception:
            time.sleep(1)
    raise TimeoutError("Tor did not start within timeout.")


# =============================
# Tor Hidden Service Management
# =============================

def create_hidden_service_dir(port, base_dir=None):
    """
    Creates folder and torrc file for a Hidden Service exposing the given local port.
    Returns Hidden Service folder path and generated torrc path.
    """
    if base_dir is None:
        base_dir = os.path.join(TOR_DIR, 'hidden_service')
    os.makedirs(base_dir, exist_ok=True)
    hs_dir = os.path.join(base_dir, 'service')
    os.makedirs(hs_dir, exist_ok=True)
    torrc_path = os.path.join(base_dir, 'torrc')
    with open(torrc_path, 'w') as f:
        f.write(f"HiddenServiceDir {hs_dir}\n")
        f.write(f"HiddenServicePort {port} 127.0.0.1:{port}\n")
        f.write(f"SocksPort {TOR_SOCKS_PORT}\n")
    return hs_dir, torrc_path


def launch_tor_with_hidden_service(port, base_dir=None):
    """
    Launches Tor with a Hidden Service exposing the given local port.
    Returns Tor process and generated .onion address.
    """
    hs_dir, torrc_path = create_hidden_service_dir(port, base_dir)
    tor_path = get_tor_binary_path()
    args = [tor_path, '-f', torrc_path]
    print(f"Launching Tor with Hidden Service: {' '.join(args)}")
    proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    # Wait for hostname file creation (.onion address)
    hostname_path = os.path.join(hs_dir, 'hostname')
    print("Waiting for .onion address creation...")
    for _ in range(60):  # Timeout ~60s
        if os.path.isfile(hostname_path):
            with open(hostname_path, 'r') as f:
                onion_addr = f.read().strip()
            print(f".onion address generated: {onion_addr}")
            return proc, onion_addr
        time.sleep(1)
    proc.terminate()
    raise TimeoutError("Hidden Service was not created within timeout.")


if __name__ == "__main__":
    print("[TOR MANAGER] Initialization...")
    ensure_tor()
    proc = launch_tor()
    try:
        wait_for_tor_ready()
        print("[TOR MANAGER] Tor is ready to use!")
    finally:
        print("[TOR MANAGER] Stopping Tor...")
        proc.terminate()
        proc.wait()