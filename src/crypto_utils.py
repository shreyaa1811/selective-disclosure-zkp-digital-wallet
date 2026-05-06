# src/crypto_utils.py
import hashlib
import json
import secrets
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization


def generate_keypair():
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    return private_key, public_key


def serialize_public_key(public_key) -> str:
    raw = public_key.public_bytes(
        serialization.Encoding.Raw,
        serialization.PublicFormat.Raw
    )
    return raw.hex().zfill(64)


def deserialize_public_key(hex_str: str):
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    raw = bytes.fromhex(hex_str.zfill(64))
    return Ed25519PublicKey.from_public_bytes(raw)


def sign(private_key, data: dict) -> str:
    message = json.dumps(data, sort_keys=True).encode()
    sig = private_key.sign(message)
    return ''.join(f'{b:02x}' for b in sig)

def verify_signature(public_key, data: dict, signature_hex: str) -> bool:
    try:
        message = json.dumps(data, sort_keys=True).encode()
        # Pad to 128 chars to handle any missing leading zeros
        padded = signature_hex.zfill(128)
        sig_bytes = bytes.fromhex(padded)
        public_key.verify(sig_bytes, message)
        return True
    except Exception as e:
        print("verify error:", e)
        return False


def sha256_hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def generate_nonce() -> str:
    return secrets.token_hex(32)


def commit(secret_value: str, nonce: str) -> str:
    return sha256_hash(secret_value + nonce)


def poseidon_simulate(inputs: list) -> int:
    FIELD_PRIME = 21888242871839275222246405745257275088548364400416034343698204186575808495617
    combined = "_".join(str(i) for i in inputs)
    h = int(hashlib.sha256(combined.encode()).hexdigest(), 16)
    return h % FIELD_PRIME