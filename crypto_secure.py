# crypto_secure.py
import base64, json
from typing import Tuple
from nacl.public import PrivateKey, PublicKey, Box
from nacl.utils import random as nacl_random

# --- Key utilities ---

def gen_keypair_b64() -> Tuple[str, str]:
    """Generate a Curve25519 keypair as base64 (pk, sk)."""
    sk = PrivateKey.generate()
    pk = sk.public_key
    return (base64.b64encode(bytes(pk)).decode(), base64.b64encode(bytes(sk)).decode())

def load_private_key_b64(sk_b64: str) -> PrivateKey:
    return PrivateKey(base64.b64decode(sk_b64))

def load_public_key_b64(pk_b64: str) -> PublicKey:
    return PublicKey(base64.b64decode(pk_b64))

# --- Encrypt / Decrypt ---

def encrypt_for_server(server_pk_b64: str, plaintext_bytes: bytes) -> dict:
    """
    Client-side: create ephemeral key, derive shared secret (Box), and encrypt.
    Returns dict: {epk, nonce, ciphertext} as base64 strings.
    """
    server_pk = load_public_key_b64(server_pk_b64)
    eph_sk = PrivateKey.generate()
    eph_pk_b64 = base64.b64encode(bytes(eph_sk.public_key)).decode()

    box = Box(eph_sk, server_pk)
    nonce = nacl_random(Box.NONCE_SIZE)  # 24 bytes
    ct = box.encrypt(plaintext_bytes, nonce)
    # ct includes nonce+ciphertext; we already used nonce, so strip header:
    ciphertext = ct.ciphertext

    return {
        "epk": eph_pk_b64,
        "nonce": base64.b64encode(nonce).decode(),
        "ciphertext": base64.b64encode(ciphertext).decode(),
    }

def decrypt_from_client(server_sk_b64: str, epk_b64: str, nonce_b64: str, ciphertext_b64: str) -> bytes:
    """
    Server-side: use server private key + client epk to decrypt.
    """
    server_sk = load_private_key_b64(server_sk_b64)
    client_epk = load_public_key_b64(epk_b64)
    nonce = base64.b64decode(nonce_b64)
    ciphertext = base64.b64decode(ciphertext_b64)

    box = Box(server_sk, client_epk)
    # Box wants full message = ciphertext only (nonce passed separately)
    return box.decrypt(ciphertext, nonce)