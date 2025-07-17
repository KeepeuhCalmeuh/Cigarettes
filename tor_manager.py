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
# Module de gestion de Tor embarqué
# =============================
# Ce module :
# 1. Détecte l'OS et l'architecture
# 2. Vérifie la présence de Tor dans ./tor/
# 3. Télécharge Tor si besoin
# 4. Décompresse/installe Tor
# 5. Lance Tor en sous-processus
# 6. Vérifie que Tor est prêt (SOCKS5 up)
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
    """Détecte l'OS et retourne la clé pour TOR_URLS."""
    os_name = platform.system()
    if os_name == 'Windows':
        return 'Windows'
    elif os_name == 'Linux':
        return 'Linux'
    elif os_name == 'Darwin':
        return 'Darwin'
    else:
        raise RuntimeError(f"OS non supporté : {os_name}")


def get_tor_binary_path():
    """Retourne le chemin du binaire Tor selon l'OS."""
    os_key = detect_os()
    if os_key == 'Windows':
        return os.path.join(TOR_DIR, 'Tor', 'tor.exe')
    elif os_key == 'Linux':
        return os.path.join(TOR_DIR, 'tor', 'tor')
    elif os_key == 'Darwin':
        return os.path.join(TOR_DIR, 'Tor', 'tor')


def is_tor_present():
    """Vérifie si le binaire Tor est déjà présent."""
    return os.path.isfile(get_tor_binary_path())


def download_tor():
    """Télécharge l'archive Tor adaptée à l'OS dans le dossier tor/."""
    os_key = detect_os()
    url = TOR_URLS[os_key]
    local_archive = os.path.join(TOR_DIR, os.path.basename(url))
    os.makedirs(TOR_DIR, exist_ok=True)
    print(f"Téléchargement de Tor depuis {url} ...")
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(local_archive, 'wb') as f:
            shutil.copyfileobj(r.raw, f)
    print(f"Archive téléchargée : {local_archive}")
    return local_archive


def extract_tor(archive_path):
    """Décompresse l'archive Tor dans le dossier tor/."""
    print(f"Décompression de {archive_path} ...")
    if archive_path.endswith('.zip'):
        with zipfile.ZipFile(archive_path, 'r') as zip_ref:
            zip_ref.extractall(TOR_DIR)
    elif archive_path.endswith('.tar.xz') or archive_path.endswith('.tar.gz'):
        mode = 'r:xz' if archive_path.endswith('.tar.xz') else 'r:gz'
        with tarfile.open(archive_path, mode) as tar_ref:
            tar_ref.extractall(TOR_DIR)
    else:
        raise RuntimeError("Format d'archive non supporté")
    print("Décompression terminée.")


def ensure_tor():
    """Vérifie la présence de Tor, le télécharge et l'installe si besoin."""
    if is_tor_present():
        print("Tor déjà présent.")
        return
    archive = download_tor()
    extract_tor(archive)
    # Optionnel : supprimer l'archive après extraction
    os.remove(archive)
    if not is_tor_present():
        raise RuntimeError("Tor n'a pas été trouvé après installation !")
    print("Tor prêt à l'emploi.")


def launch_tor(extra_args=None):
    """Lance Tor en sous-processus. Retourne le handle du process."""
    tor_path = get_tor_binary_path()
    if not os.path.isfile(tor_path):
        raise RuntimeError(f"Binaire Tor introuvable : {tor_path}")
    args = [tor_path]
    if extra_args:
        args += extra_args
    print(f"Lancement de Tor : {' '.join(args)}")
    proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return proc


def wait_for_tor_ready(timeout=60):
    """Attend que le port SOCKS5 de Tor soit ouvert (prêt)."""
    import socket
    start = time.time()
    while time.time() - start < timeout:
        try:
            with socket.create_connection(('127.0.0.1', TOR_SOCKS_PORT), timeout=2):
                print("Tor SOCKS5 prêt !")
                return True
        except Exception:
            time.sleep(1)
    raise TimeoutError("Tor n'a pas démarré dans le temps imparti.")


# =============================
# Gestion du Hidden Service Tor
# =============================

def create_hidden_service_dir(port, base_dir=None):
    """
    Crée le dossier et le fichier torrc pour un Hidden Service exposant le port local donné.
    Retourne le chemin du dossier Hidden Service et du torrc généré.
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
    Start Tor with a Hidden Service exposing the local port given.
    Return the Tor process and the generated .onion address.
    """
    hs_dir, torrc_path = create_hidden_service_dir(port, base_dir)
    tor_path = get_tor_binary_path()
    args = [tor_path, '-f', torrc_path]
    #print(f"Lancement de Tor avec Hidden Service : {' '.join(args)}")
    proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    # Attendre la création du fichier hostname (adresse .onion)
    hostname_path = os.path.join(hs_dir, 'hostname')
    print("Waiting for .onion...")
    for _ in range(60):  # Timeout ~60s
        if os.path.isfile(hostname_path):
            with open(hostname_path, 'r') as f:
                onion_addr = f.read().strip()
            #print(f"Your .onion address : {onion_addr}")
            return proc, onion_addr
        time.sleep(1)
    proc.terminate()
    raise TimeoutError("Le Hidden Service n'a pas été créé dans le temps imparti.")

# =============================
# Exemple d'utilisation du module
# =============================
if __name__ == "__main__":
    print("[TOR MANAGER] Initialisation...")
    ensure_tor()
    proc = launch_tor()
    try:
        wait_for_tor_ready()
        print("[TOR MANAGER] Tor est prêt à l'emploi !")
    finally:
        print("[TOR MANAGER] Arrêt de Tor...")
        proc.terminate()
        proc.wait()

# =============================
# Exemple d'utilisation du Hidden Service
# =============================
# Supprimer la fonction de démonstration qui fait input() et terminate.
# La fonction utile est :
# def launch_tor_with_hidden_service(port, base_dir=None):
#     ...
#     return proc, onion_addr