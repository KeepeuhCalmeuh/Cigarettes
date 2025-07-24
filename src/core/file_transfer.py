import os
from typing import Optional

# États globaux (à adapter selon l'architecture du projet)
FILE_TRANSFER_PROCEDURE = False  # Émetteur : en cours de transfert
FILE_TRANSFER_BOOL = False       # Récepteur : en attente d'acceptation

# Mémoire temporaire pour le fichier à transférer (émetteur)
file_transfer_context = {
    'file_path': None,
    'file_name': None,
    'file_size': None,
    'file_data': None,  # Chiffré
    'chunks': None,
    'current_chunk': 0
}

# Mémoire temporaire pour la réception (récepteur)
file_receive_context = {
    'file_name': None,
    'file_size': None,
    'received_size': 0,
    'file_obj': None
}

# --- Fonctions principales ---

def initiate_file_transfer(file_path: str) -> Optional[str]:
    """
    Prépare le transfert côté émetteur : charge, chiffre et prépare le fichier.
    Retourne le message d'annonce à envoyer.
    """
    global FILE_TRANSFER_PROCEDURE, file_transfer_context
    if not os.path.isfile(file_path):
        return None
    file_name = os.path.basename(file_path)
    file_size = os.path.getsize(file_path)
    with open(file_path, 'rb') as f:
        file_data = f.read()
    # TODO: Chiffrer file_data ici si besoin
    file_transfer_context.update({
        'file_path': file_path,
        'file_name': file_name,
        'file_size': file_size,
        'file_data': file_data,
        'chunks': [file_data[i:i+4096] for i in range(0, len(file_data), 4096)],
        'current_chunk': 0
    })
    FILE_TRANSFER_PROCEDURE = True
    return f"__FILE_TRANSFER__ {file_name} {file_size}"

def handle_file_transfer_request(message: str):
    """
    Détecte et traite un message de demande de transfert côté récepteur.
    """
    global FILE_TRANSFER_BOOL, file_receive_context
    parts = message.strip().split()
    if len(parts) >= 3 and parts[0] == "__FILE_TRANSFER__":
        file_name = parts[1]
        file_size = int(parts[2])
        file_receive_context.update({
            'file_name': file_name,
            'file_size': file_size,
            'received_size': 0,
            'file_obj': None
        })
        FILE_TRANSFER_BOOL = True
        return f"[INFO] transfer file {file_name} {file_size}, accept ? (/__FILE_ACCEPT__ or /__FILE_DECLINE__)"
    return None

def accept_file_transfer():
    """
    Côté récepteur : accepte le transfert.
    """
    return "__FILE_TRANSFER_ACCEPTED__"

def decline_file_transfer():
    """
    Côté récepteur : refuse le transfert.
    """
    global FILE_TRANSFER_BOOL, file_receive_context
    FILE_TRANSFER_BOOL = False
    file_receive_context = {k: None for k in file_receive_context}
    return "[INFO] File transfer declined."

def handle_file_transfer_accepted():
    """
    Côté émetteur : déclenche l'envoi du fichier en chunks.
    """
    global file_transfer_context, FILE_TRANSFER_PROCEDURE
    chunks = file_transfer_context.get('chunks')
    if not chunks:
        return []
    messages = []
    for chunk in chunks:
        # Ici, on pourrait chiffrer chaque chunk si besoin
        messages.append(chunk)
    FILE_TRANSFER_PROCEDURE = False
    file_transfer_context = {k: None for k in file_transfer_context}
    return messages

def receive_file_chunk(chunk: bytes):
    """
    Côté récepteur : reçoit un chunk de fichier.
    """
    global file_receive_context
    if file_receive_context['file_obj'] is None:
        # Crée le dossier si besoin
        os.makedirs('received_files', exist_ok=True)
        file_path = os.path.join('received_files', file_receive_context['file_name'])
        file_receive_context['file_obj'] = open(file_path, 'wb')
    file_receive_context['file_obj'].write(chunk)
    file_receive_context['received_size'] += len(chunk)
    # Affichage barre de progression (à faire côté UI)
    if file_receive_context['received_size'] >= file_receive_context['file_size']:
        file_receive_context['file_obj'].close()
        file_receive_context['file_obj'] = None
        return True  # Transfert terminé
    return False

def reset_file_receive_context():
    global FILE_TRANSFER_BOOL, file_receive_context
    FILE_TRANSFER_BOOL = False
    file_receive_context = {k: None for k in file_receive_context} 