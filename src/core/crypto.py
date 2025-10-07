"""
Cryptographic utilities for secure communication.
Handles key generation, encryption, decryption, and digital signatures.
"""

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import os
from cryptography.hazmat.primitives import serialization
from typing import Optional


class CryptoManager:
    """
    Manages cryptographic operations including key generation, encryption,
    decryption, and digital signatures for secure P2P communication.
    """
    
    def __init__(self, keyfile: str = None):
        """
        Initialize the crypto manager with persistent key management.
        
        Args:
            keyfile: Path to the private key file (optional, uses default location)
        """
        if keyfile is None:
            # Create secure directory for keys
            self.keys_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'keys')
            os.makedirs(self.keys_dir, exist_ok=True)
            self.keyfile = os.path.join(self.keys_dir, "user_private_key.pem")
        else:
            self.keyfile = keyfile
            self.keys_dir = os.path.dirname(keyfile)
            
        self.private_key = self._load_or_generate_private_key()
        self.public_key = self.private_key.public_key()
        self.peer_public_key: Optional[ec.EllipticCurvePublicKey] = None
        self.session_key: Optional[bytes] = None
        self.cipher: Optional[AESGCM] = None

    def _load_or_generate_private_key(self) -> ec.EllipticCurvePrivateKey:
        """Load existing private key or generate a new one."""
        if os.path.exists(self.keyfile):
            # print(f" [DEBUG] Loading existing private key from: {self.keyfile}")
            return self._load_private_key_from_file(self.keyfile)
        else:
            # print(f" [DEBUG] Generating new private key and saving to: {self.keyfile}")
            os.makedirs(self.keys_dir, exist_ok=True)
            return self._generate_private_key_file(self.keyfile)

    def _load_private_key_from_file(self, path: str) -> ec.EllipticCurvePrivateKey:
        """Load a private key from the specified file."""
        with open(path, "rb") as f:
            # Note: if the key is encrypted, 'password' should not be None.
            # But in this case, it is not encrypted (NoEncryption)
            return serialization.load_pem_private_key(f.read(), password=None)

    def _generate_private_key_file(self, path: str) -> ec.EllipticCurvePrivateKey:
        """Generate a new private key, save it to the specified path, and return it."""
        
        private_key = ec.generate_private_key(ec.SECP384R1())

        with open(path, "wb") as f:
            f.write(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ))

        try:
            # Read/write for owner only (0o600)
            os.chmod(path, 0o600)
        except OSError:
            # Ignore for windows or if chmod fails
            pass

        return private_key

    
    def reset_keys(self) -> None:
        """Reset the current keys by generating a new key pair."""
        self.private_key = self._generate_private_key_file(self.keyfile)
        self.public_key = self.private_key.public_key()
        self.peer_public_key = None
        self.session_key = None
        self.cipher = None

    def sign_challenge(self, challenge: bytes) -> bytes:
        """Sign a challenge with the user's private key."""
        return self.private_key.sign(challenge, ec.ECDSA(hashes.SHA256()))

    def verify_signature(self, public_key_bytes: bytes, challenge: bytes, signature: bytes) -> bool:
        """Verify the signature of a challenge with a given public key."""
        try:
            pubkey = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP384R1(), public_key_bytes)
            pubkey.verify(signature, challenge, ec.ECDSA(hashes.SHA256()))
            return True
        except Exception:
            return False

    def get_public_bytes(self) -> bytes:
        """Return the public key as bytes."""
        return self.public_key.public_bytes(
            encoding=serialization.Encoding.X962,
            format=serialization.PublicFormat.CompressedPoint
        )

    def set_peer_public_key(self, peer_key_bytes: bytes) -> None:
        """Configure the public key of the remote peer."""
        self.peer_public_key = ec.EllipticCurvePublicKey.from_encoded_point(
            ec.SECP384R1(),
            peer_key_bytes
        )
        self._derive_session_key()

    def get_public_key_fingerprint(self) -> str:
        """Calculate the SHA256 fingerprint of the public key."""
        digest = hashes.Hash(hashes.SHA256())
        digest.update(self.get_public_bytes())
        return digest.finalize().hex()

    def get_peer_fingerprint(self) -> str:
        """Return the peer's public key fingerprint."""
        if not self.peer_public_key:
            raise ValueError("Peer's public key not defined")
        digest = hashes.Hash(hashes.SHA256())
        digest.update(
            self.peer_public_key.public_bytes(
                encoding=serialization.Encoding.X962,
                format=serialization.PublicFormat.CompressedPoint
            )
        )
        return digest.finalize().hex()

    def _derive_session_key(self) -> None:
        """Derive the session key after the key exchange."""
        if not self.peer_public_key:
            raise ValueError("Peer's public key is not defined")
        
        # Perform the Diffie-Hellman key exchange
        shared_key = self.private_key.exchange(ec.ECDH(), self.peer_public_key)
        
        # Derive session key with HKDF
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=None,
            info=b"Cigarettes-session-key"
        )
        self.session_key = hkdf.derive(shared_key)
        self.cipher = AESGCM(self.session_key)

    def encrypt_message(self, message: str) -> bytes:
        """Encrypt a message with the session key."""
        if not self.session_key:
            raise ValueError("The session key is not yet established")
        
        # Random nonce generation
        nonce = os.urandom(12)
        
        # Message encryption
        ciphertext = self.cipher.encrypt(nonce, message.encode(), None)
        
        # Concatenation of nonce and ciphertext for transmission
        return nonce + ciphertext

    def decrypt_message(self, encrypted_data: bytes) -> str:
        """Decrypt a message with the session key."""
        if not self.session_key:
            raise ValueError("The session key is not yet established")
            
        # Separation of nonce and ciphertext
        nonce = encrypted_data[:12]
        ciphertext = encrypted_data[12:]
        
        # Decrypting the message
        plaintext = self.cipher.decrypt(nonce, ciphertext, None)
        return plaintext.decode()

    def encrypt_bytes(self, data: bytes) -> bytes:
        """Encrypt binary data with the session key (for file transfer)."""
        if not self.session_key:
            raise ValueError("The session key is not yet established")
        nonce = os.urandom(12)
        ciphertext = self.cipher.encrypt(nonce, data, None)
        return nonce + ciphertext

    def decrypt_bytes(self, encrypted_data: bytes) -> bytes:
        """Decrypt binary data with the session key (for file transfer)."""
        if not self.session_key:
            raise ValueError("The session key is not yet established")
        nonce = encrypted_data[:12]
        ciphertext = encrypted_data[12:]
        return self.cipher.decrypt(nonce, ciphertext, None) 