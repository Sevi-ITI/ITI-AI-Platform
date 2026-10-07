"""secret_matches(): does this secret hash to the stored hash? Constant-time comparison."""

import hmac

from app.auth.d_keys.hash_secret import hash_secret


def secret_matches(secret: str, stored_hash: str) -> bool:
    return hmac.compare_digest(hash_secret(secret), stored_hash)
