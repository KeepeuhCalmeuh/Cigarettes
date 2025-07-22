import pytest
import os
from src.core.crypto import CryptoManager

# Exemple de test basique
def test_dummy():
    assert True

# Ajoute ici tes tests pour crypto.py 

def test_key_generation_and_fingerprint(tmp_path):
    keyfile = tmp_path / 'testkey.pem'
    cm = CryptoManager(str(keyfile))
    assert os.path.exists(keyfile)
    fp = cm.get_public_key_fingerprint()
    assert isinstance(fp, str) and len(fp) == 64

def test_sign_and_verify():
    cm = CryptoManager()
    challenge = b'abc123'
    sig = cm.sign_challenge(challenge)
    pub_bytes = cm.get_public_bytes()
    assert cm.verify_signature(pub_bytes, challenge, sig)

def test_set_peer_public_key_and_fingerprint():
    cm1 = CryptoManager()
    cm2 = CryptoManager()
    cm1.set_peer_public_key(cm2.get_public_bytes())
    fp = cm1.get_peer_fingerprint()
    assert isinstance(fp, str) and len(fp) == 64

def test_encrypt_decrypt_message_bytes(monkeypatch):
    cm1 = CryptoManager()
    cm2 = CryptoManager()
    cm1.set_peer_public_key(cm2.get_public_bytes())
    cm2.set_peer_public_key(cm1.get_public_bytes())
    msg = 'hello world'
    encrypted = cm1.encrypt_message(msg)
    decrypted = cm2.decrypt_message(encrypted)
    assert decrypted == msg
    data = b'\x01\x02\x03abc'
    encrypted_bytes = cm1.encrypt_bytes(data)
    decrypted_bytes = cm2.decrypt_bytes(encrypted_bytes)
    assert decrypted_bytes == data 