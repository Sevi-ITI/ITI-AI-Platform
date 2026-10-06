"""split_key(): 'iti_sk_<key_id>_<secret>' -> (key_id, secret), or None if the shape is wrong."""

from app.auth.d_keys.key_prefix import KEY_PREFIX

def split_key(raw: str) -> tuple[str, str] | None:
    if not raw.startswith(KEY_PREFIX):
        return None
    key_id, sep, secret = raw[len(KEY_PREFIX) :].partition("_")  # first "_" only: secrets may contain "_"
    if not sep or len(key_id) != 12 or not secret:
        return None
    return key_id, secret