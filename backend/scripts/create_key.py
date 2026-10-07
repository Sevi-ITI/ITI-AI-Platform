"""create_key: makes an API key from the command line. Needed for the FIRST admin key
(the API needs an admin key before it will make keys). Prints the key once; only its hash is stored.

Run from backend\\:
    python -m scripts.create_key iti-admin --scopes admin
    python -m scripts.create_key hr-portal --scopes chat:invoke documents:write --collections iti-docs
"""

import argparse

from pydantic import ValidationError

from app.admin.a_schemas.key_create import KeyCreate
from app.admin.d_service.mint_key import mint_key
from app.core.c_database.get_sessionmaker import get_sessionmaker


def main() -> None:
    parser = argparse.ArgumentParser(description="Make an ITI API key (shown once).")
    parser.add_argument("app_id", help='which app the key is for, e.g. "iti-admin" or "hr-portal"')
    parser.add_argument("--scopes", nargs="+", default=["chat:invoke"], help="chat:invoke, documents:write, admin")
    parser.add_argument("--collections", nargs="*", default=[], help="e.g. iti-docs")
    parser.add_argument("--valid-days", type=int, default=365, help="0 = never expires")
    args = parser.parse_args()

    try:
        body = KeyCreate(
            app_id=args.app_id,
            scopes=args.scopes,
            allowed_collections=args.collections,
            valid_days=args.valid_days or None,
        )
    except ValidationError as exc:
        parser.error(str(exc))
    with get_sessionmaker()() as db:
        key = mint_key(db, body)

    print(f"app_id : {key.app_id}")
    print(f"scopes : {', '.join(key.scopes)}")
    print(f"key_id : {key.key_id}")
    print(f"expires: {key.expires_at or 'never'}")
    print(f"api_key: {key.api_key}   <- shown once: store it in a password manager")


if __name__ == "__main__":
    main()