from __future__ import annotations

import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class CredentialService:
    @staticmethod
    def get_master_key() -> bytes:
        from app.core.config import settings
        hex_key = settings.CREDENTIAL_MASTER_KEY
        return bytes.fromhex(hex_key)

    @staticmethod
    def encrypt(plaintext: str) -> bytes:
        master_key = CredentialService.get_master_key()
        nonce = os.urandom(12)
        aesgcm = AESGCM(master_key)
        ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
        return nonce + ciphertext

    @staticmethod
    def decrypt(stored: bytes) -> str:
        master_key = CredentialService.get_master_key()
        nonce = stored[:12]
        ct = stored[12:]
        aesgcm = AESGCM(master_key)
        return aesgcm.decrypt(nonce, ct, None).decode("utf-8")
