"""generate_key(): makes a new key. Returns (key_id, full_key_to_show_once, hash_to_store).
A key looks like  iti_sk_3f9a1c2b7e4d_Xb8...  =  "iti_sk_" + key_id + "_" + secret."""

import secrets

from app.auth.d_keys.hash_secret import hash_secret
from app.auth.d_keys.key_prefix import KEY_PREFIX


def generate_key() -> tuple[str, str, str]:
    key_id = secrets.token_hex(6)
    secret = secrets.token_urlsafe(32)
    return key_id, f"{KEY_PREFIX}{key_id}_{secret}", hash_secret(secret)
