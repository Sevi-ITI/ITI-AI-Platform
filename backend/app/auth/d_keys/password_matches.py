"""password_matches(): does this password match the stored "scrypt$n$r$p$salt$hash"? Constant-time comparison.
A damaged or unknown stored value never matches (False, not a crash)."""

import base64
import binascii
import hashlib
import hmac


def password_matches(password: str, stored: str) -> bool:
    try:
        scheme, n, r, p, salt, digest = stored.split("$")
        expected = base64.b64decode(digest, validate=True)
        actual = hashlib.scrypt(
            password.encode(), salt=base64.b64decode(salt, validate=True), n=int(n), r=int(r), p=int(p), dklen=32
        )
    except (ValueError, binascii.Error):
        return False
    return scheme == "scrypt" and hmac.compare_digest(actual, expected)
