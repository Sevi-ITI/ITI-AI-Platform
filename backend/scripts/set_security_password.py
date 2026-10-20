"""set_security_password: sets or resets a super admin's SECURITY PASSWORD (Phase 8.6e-3, app/tools/gate.py).
It unlocks the risky Tools & MCP actions for 15 minutes. On purpose this is the ONLY way to set it (no console
page), so a stolen console session cannot set or change it. Resetting also clears a lockout.
The password is typed twice at a hidden prompt: never on the command line, never printed.

Run from backend\\:
    python -m scripts.set_security_password vince
"""

import argparse
import getpass

from app.core.e_errors.app_error import AppError
from app.tools.gate import MIN_LENGTH, UNLOCK_MINUTES, set_password


def main() -> None:
    parser = argparse.ArgumentParser(description="Set or reset a super admin's security password.")
    parser.add_argument("username", help='an active super admin account, e.g. "vince"')
    args = parser.parse_args()

    password = getpass.getpass(f"Security password ({MIN_LENGTH}+ characters, NOT your login password): ")
    if password != getpass.getpass("Same password again: "):
        parser.error("the two passwords are different")
    try:
        set_password(args.username.strip().lower(), password)
    except AppError as exc:
        parser.error(exc.message)

    print(f"Security password set for {args.username.strip().lower()}.")
    print(f"Console -> Tools & MCP -> Unlock: unlocks the risky actions for {UNLOCK_MINUTES} minutes.")


if __name__ == "__main__":
    main()
