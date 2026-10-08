"""new_session_pass(): makes a session pass. Returns (pass_to_hand_out, hash_to_store).
A pass looks like  iti_cs_Xb8...  =  "iti_cs_" + 43 random characters. It is random enough that one
sha256 is safe to store (the same reasoning as the API keys); only passwords need the slow scrypt."""

import secrets

from app.auth.d_keys.hash_secret import hash_secret

SESSION_PREFIX = "iti_cs_"


def new_session_pass() -> tuple[str, str]:
    session_pass = SESSION_PREFIX + secrets.token_urlsafe(32)
    return session_pass, hash_secret(session_pass)
