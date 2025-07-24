import os
from typing import Optional

# Global states (adapt as needed for your project architecture)
FILE_TRANSFER_PROCEDURE = False  # Sender: file transfer in progress
FILE_TRANSFER_BOOL = False       # Receiver: waiting for file transfer acceptance

# Temporary memory for the file to be transferred (sender)
file_transfer_context = {
    'file_path': None,
    'file_name': None,
    'file_size': None,
    'file_data': None,  # Encrypted
    'chunks': None,
    'current_chunk': 0
}

# Temporary memory for file reception (receiver)
file_receive_context = {
    'file_name': None,
    'file_size': None,
    'received_size': 0,
    'file_obj': None
}

# --- Main functions ---

def initiate_file_transfer(file_path: str) -> Optional[str]:
    """
    Prepares the transfer on the sender side: loads, encrypts, and prepares the file.
    Returns the announcement message to send.
    """
    global FILE_TRANSFER_PROCEDURE, file_transfer_context
    if not os.path.isfile(file_path):
        return None
    file_name = os.path.basename(file_path)
    file_size = os.path.getsize(file_path)
    with open(file_path, 'rb') as f:
        file_data = f.read()
    # TODO: Encrypt file_data here if needed
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
    Detects and processes a file transfer request message on the receiver side.
    """
    global FILE_TRANSFER_BOOL, file_receive_context
    # Search for the __FILE_TRANSFER__ token anywhere in the message
    if "__FILE_TRANSFER__" in message:
        # Get the part after the token
        idx = message.index("__FILE_TRANSFER__")
        file_info = message[idx + len("__FILE_TRANSFER__"):].strip().split()
        if len(file_info) >= 2:
            file_name = file_info[0]
            try:
                file_size = int(file_info[1])
            except ValueError:
                return None
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
    Receiver side: accepts the file transfer.
    """
    return "__FILE_TRANSFER_ACCEPTED__"

def decline_file_transfer():
    """
    Receiver side: declines the file transfer.
    """
    global FILE_TRANSFER_BOOL, file_receive_context
    FILE_TRANSFER_BOOL = False
    file_receive_context = {k: None for k in file_receive_context}
    return "[INFO] File transfer declined."

def handle_file_transfer_accepted():
    """
    Sender side: triggers the sending of the file in chunks.
    """
    global file_transfer_context, FILE_TRANSFER_PROCEDURE
    chunks = file_transfer_context.get('chunks')
    if not chunks:
        return []
    messages = []
    for chunk in chunks:
        messages.append(chunk)
    reset_all_file_transfer_state()
    return messages

def receive_file_chunk(chunk: bytes):
    """
    Receiver side: receives a file chunk.
    """
    global file_receive_context
    if file_receive_context['file_obj'] is None:
        os.makedirs('received_files', exist_ok=True)
        file_path = os.path.join('received_files', file_receive_context['file_name'])
        file_receive_context['file_obj'] = open(file_path, 'wb')
    file_receive_context['file_obj'].write(chunk)
    file_receive_context['received_size'] += len(chunk)
    if file_receive_context['received_size'] >= file_receive_context['file_size']:
        file_receive_context['file_obj'].close()
        file_receive_context['file_obj'] = None
        reset_all_file_transfer_state()
        return True  # Transfer complete
    return False

def reset_file_receive_context():
    """
    Resets the file reception context and state.
    """
    global FILE_TRANSFER_BOOL, file_receive_context
    FILE_TRANSFER_BOOL = False
    file_receive_context = {k: None for k in file_receive_context}

def reset_all_file_transfer_state():
    """
    Resets all file transfer states and contexts (sender and receiver).
    """
    global FILE_TRANSFER_PROCEDURE, FILE_TRANSFER_BOOL, file_transfer_context, file_receive_context
    FILE_TRANSFER_PROCEDURE = False
    FILE_TRANSFER_BOOL = False
    file_transfer_context = {k: None for k in file_transfer_context}
    file_receive_context = {k: None for k in file_receive_context} 