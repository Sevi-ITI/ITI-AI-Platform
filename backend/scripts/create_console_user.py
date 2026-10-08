"""create_console_user: makes a console account from the command line. Needed for the FIRST account
(someone must be able to log in before the Accounts page can add the others).
The password is typed twice at a hidden prompt: never on the command line, never printed.

Run from backend\\:
    python -m scripts.create_console_user vince --role super_admin --name "Vince"
"""

import argparse
import getpass
from typing import get_args

from pydantic import ValidationError

from app.auth.a_schemas.console_role import ConsoleRole
from app.console.a_schemas.account_create import AccountCreate
from app.console.d_service.create_account import create_account
from app.core.c_database.get_sessionmaker import get_sessionmaker
from app.core.e_errors.app_error import AppError


def main() -> None:
    parser = argparse.ArgumentParser(description="Make an ITI AI Console account.")
    parser.add_argument("username", help='lowercase, 3-32 characters, e.g. "vince"')
    parser.add_argument("--role", required=True, choices=get_args(ConsoleRole))
    parser.add_argument("--name", default=None, help='display name, e.g. "Vince"')
    args = parser.parse_args()

    password = getpass.getpass("Password (12+ characters): ")
    if password != getpass.getpass("Same password again: "):
        parser.error("the two passwords are different")
    try:
        body = AccountCreate(username=args.username, display_name=args.name, role=args.role, password=password)
    except ValidationError as exc:
        parser.error(str(exc))  # hide_input_in_errors: the password is never in this text
    with get_sessionmaker()() as db:
        try:
            account = create_account(db, body)
        except AppError as exc:
            parser.error(exc.message)

    print(f"username: {account.username}")
    print(f"name    : {account.display_name or '-'}")
    print(f"role    : {account.role}")
    print("Log in at POST /v1/console/login (the console's login page in 6B).")


if __name__ == "__main__":
    main()
