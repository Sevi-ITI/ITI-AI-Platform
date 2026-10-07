"""KeyCreated: KeyInfo plus the full key, returned ONCE when the key is made."""

from app.admin.a_schemas.key_info import KeyInfo


class KeyCreated(KeyInfo):
    api_key: str
