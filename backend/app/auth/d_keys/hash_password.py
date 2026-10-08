"""hash_password(): a console password -> "scrypt$n$r$p$salt$hash" (salted, slow on purpose).

Why not sha256 like the API keys: a key's secret is 43 random characters, so one fast hash is enough.
A password is short and guessable, so each guess must be expensive: scrypt with OWASP's setting
N=2^14, r=8, p=5 costs 16 MiB of memory per check. The settings travel inside the stored string,
so they can be raised later without breaking passwords that are already saved."""

import base64
import hashlib
import secrets

N, R, P = 2**14, 8, 5  # one of the OWASP Password Storage Cheat Sheet's scrypt settings


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=N, r=R, p=P, dklen=32)
    return f"scrypt${N}${R}${P}${base64.b64encode(salt).decode()}${base64.b64encode(digest).decode()}"
