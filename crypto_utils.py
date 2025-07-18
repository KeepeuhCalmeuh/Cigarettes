from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import os
from cryptography.hazmat.primitives import serialization


class CryptoManager:
    def sign_challenge(self, challenge: bytes) -> bytes:
        """Sign a challenge with the user's private key."""
        return self.private_key.sign(challenge, ec.ECDSA(hashes.SHA256()))


    def verify_signature(self, public_key_bytes: bytes, challenge: bytes, signature: bytes) -> bool:
        """Verifies the signature of a challenge with a given public key."""
        try:
            pubkey = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP384R1(), public_key_bytes)
            pubkey.verify(signature, challenge, ec.ECDSA(hashes.SHA256()))
            return True
        except Exception:
            return False
    

    def __init__(self):
        # Persistent key management (strong authentication)
        keyfile = "user_private_key.pem"
        if os.path.exists(keyfile):
            with open(keyfile, "rb") as f:
                self.private_key = serialization.load_pem_private_key(f.read(), password=None)
        else:
            self.private_key = ec.generate_private_key(ec.SECP384R1())
            with open(keyfile, "wb") as f:
                f.write(self.private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption()
                ))
        self.public_key = self.private_key.public_key()
        self.peer_public_key = None
        self.session_key = None

    def get_public_bytes(self):
        """Returns the public key as bytes"""
        return self.public_key.public_bytes(
            encoding=serialization.Encoding.X962,
            format=serialization.PublicFormat.CompressedPoint
        )

    def set_peer_public_key(self, peer_key_bytes):
        """Configures the public key of the remote peer"""
        self.peer_public_key = ec.EllipticCurvePublicKey.from_encoded_point(
            ec.SECP384R1(),
            peer_key_bytes
        )
        self._derive_session_key()

    def get_public_key_fingerprint(self):
        """Calculates the SHA256 fingerprint of the public key"""
        digest = hashes.Hash(hashes.SHA256())
        digest.update(self.get_public_bytes())
        return digest.finalize().hex()

    def _derive_session_key(self):
        """Derive the session key after the key exchange"""
        if not self.peer_public_key:
            raise ValueError("La clé publique du pair n'est pas définie")
        
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

    def get_peer_fingerprint(self):
        """Returns the peer's public key fingerprint"""
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


    def encrypt_message(self, message: str) -> bytes:
        """Encrypts a message with the session key"""
        if not self.session_key:
            raise ValueError("The session key is not yet established")
        
        # Random nonce generation
        nonce = os.urandom(12)
        
        # Message encryption
        ciphertext = self.cipher.encrypt(nonce, message.encode(), None)
        
        # Concatenation of nonce and ciphertext for transmission
        return nonce + ciphertext

    def decrypt_message(self, encrypted_data: bytes) -> str:
        """Decrypts a message with the session key"""
        if not self.session_key:
            raise ValueError("The session key is not yet established")
            
        # Separation of nonce and ciphertext
        nonce = encrypted_data[:12]
        ciphertext = encrypted_data[12:]
        
        # Decrypting the message
        plaintext = self.cipher.decrypt(nonce, ciphertext, None)
        return plaintext.decode()

    def encrypt_bytes(self, data: bytes) -> bytes:
        """Encrypts binary data with the session key (for file transfer)"""
        if not self.session_key:
            raise ValueError("The session key is not yet established")
        nonce = os.urandom(12)
        ciphertext = self.cipher.encrypt(nonce, data, None)
        return nonce + ciphertext

    def decrypt_bytes(self, encrypted_data: bytes) -> bytes:
        """Decrypts binary data with the session key (for file transfer)"""
        if not self.session_key:
            raise ValueError("The session key is not yet established")
        nonce = encrypted_data[:12]
        ciphertext = encrypted_data[12:]
        return self.cipher.decrypt(nonce, ciphertext, None)
