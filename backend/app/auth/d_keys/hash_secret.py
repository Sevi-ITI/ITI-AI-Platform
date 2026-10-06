"""hash_secret(): sha256 of a key's secret part. Only this hash is stored."""

import hashlib

def hash_secret(secret: str) -> str:
    return hashlib.sha256(secret.encode()).hexdigest()