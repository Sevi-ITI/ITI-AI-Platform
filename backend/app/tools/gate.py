"""gate: the SECURITY PASSWORD that unlocks the risky Tools & MCP actions (Phase 8.6e-3). One concern per file: the
table, setting the password, unlock / lock, the lockout and the `require_unlocked` dependency are all here.

- A second password, separate from the console login, one per super admin. Only its scrypt hash is stored.
  It is set or reset ONLY on the server (`python -m scripts.set_security_password`), never from the console,
  so a stolen console session cannot set it.
- A right password unlocks that ACCOUNT for 15 minutes from the moment of unlock (not extended by use).
- 5 wrong passwords in a row lock the gate for 15 minutes (the console login is not affected).
- Fail closed: no password set = every guarded action is refused. API keys never pass the gate, only people.
- Every set, unlock, lock, wrong try and lockout goes to the tools change log (never the password).
- Never 401 here: the console treats a 401 as "session ended" and logs the person out."""

from datetime import datetime, timedelta

from fastapi import Depends
from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.auth.a_schemas.app_principal import AppPrincipal
from app.auth.b_models.console_user import ConsoleUser
from app.auth.d_keys.hash_password import hash_password
from app.auth.d_keys.is_future import is_future
from app.auth.d_keys.password_matches import password_matches
from app.auth.e_dependencies.require_scope import require_scope
from app.core.c_database.base import Base
from app.core.c_database.get_sessionmaker import get_sessionmaker
from app.core.c_database.utcnow import utcnow
from app.core.e_errors.app_error import AppError
from app.tools.store import log_change

UNLOCK_MINUTES = 15
MAX_WRONG = 5
LOCK_MINUTES = 15
MIN_LENGTH = 12

# --- table ----------------------------------------------------------------------------------------------------


class SecurityGate(Base):
    """One row per super admin who has a security password."""

    __tablename__ = "security_gate"

    username: Mapped[str] = mapped_column(String(32), ForeignKey("console_users.username", ondelete="CASCADE"), primary_key=True)
    password_hash: Mapped[str] = mapped_column(String(200))  # "scrypt$n$r$p$salt$hash", like the login password
    wrong_tries: Mapped[int] = mapped_column(Integer, default=0)  # wrong passwords in a row
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))  # after MAX_WRONG wrong tries
    unlocked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))  # None = locked
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


# --- setting the password (server only: scripts/set_security_password.py) -----------------------------------


def set_password(username: str, password: str) -> None:
    """Sets or resets a super admin's security password. Clears any lockout and any open unlock."""
    if len(password) < MIN_LENGTH:
        raise AppError(422, "security_password_too_short", f"The security password needs at least {MIN_LENGTH} characters.")
    with get_sessionmaker()() as db:
        user = db.get(ConsoleUser, username)
        if user is None or not user.active or user.role != "super_admin":
            raise AppError(404, "not_a_super_admin", f"'{username}' is not an active super admin account.")
        if password_matches(password, user.password_hash):
            raise AppError(422, "same_as_login_password", "The security password must differ from the login password.")
        row = db.get(SecurityGate, username)
        what = "gate.reset_password" if row else "gate.set_password"
        if row is None:
            row = SecurityGate(username=username)
            db.add(row)
        row.password_hash = hash_password(password)
        row.wrong_tries, row.locked_until, row.unlocked_until, row.updated_at = 0, None, None, utcnow()
        log_change(db, username, what, f"user:{username}", None, None)
        db.commit()


# --- status, unlock, lock (the console's Unlock dialog) -----------------------------------------------------


def status(username: str) -> dict:
    """What the console shows: is a password set, unlocked until when, locked out until when."""
    with get_sessionmaker()() as db:
        row = db.get(SecurityGate, username)
        if row is None:
            return {"password_set": False, "unlocked_until": None, "locked_until": None}
        return {
            "password_set": True,
            "unlocked_until": row.unlocked_until if is_future(row.unlocked_until) else None,
            "locked_until": row.locked_until if is_future(row.locked_until) else None,
        }


def unlock(username: str, password: str) -> datetime:
    """The right password -> unlocked for UNLOCK_MINUTES (returns until when). A locked-out gate is refused WITHOUT
    checking the password, so guessing stops while the lockout lasts."""
    with get_sessionmaker()() as db:
        row = db.get(SecurityGate, username)
        if row is None:
            raise AppError(409, "security_password_not_set", "No security password yet. Set it on the server: python -m scripts.set_security_password")
        if is_future(row.locked_until):
            raise AppError(423, "gate_locked", f"Locked for {LOCK_MINUTES} minutes after {MAX_WRONG} wrong security passwords. Try again later.")
        if not password_matches(password, row.password_hash):
            row.wrong_tries = (row.wrong_tries or 0) + 1
            log_change(db, username, "gate.wrong_password", f"user:{username}", None, {"wrong_tries": row.wrong_tries})
            if row.wrong_tries >= MAX_WRONG:
                row.locked_until, row.unlocked_until, row.wrong_tries = utcnow() + timedelta(minutes=LOCK_MINUTES), None, 0
                log_change(db, username, "gate.locked_out", f"user:{username}", None, {"minutes": LOCK_MINUTES})
            db.commit()
            raise AppError(403, "wrong_security_password", "Wrong security password.")
        until = utcnow() + timedelta(minutes=UNLOCK_MINUTES)
        row.wrong_tries, row.locked_until, row.unlocked_until = 0, None, until
        log_change(db, username, "gate.unlock", f"user:{username}", None, {"minutes": UNLOCK_MINUTES})
        db.commit()
        return until


def lock(username: str) -> None:
    """The console's "Lock now": ends the unlock at once."""
    with get_sessionmaker()() as db:
        row = db.get(SecurityGate, username)
        if row is not None and row.unlocked_until is not None:
            row.unlocked_until = None
            log_change(db, username, "gate.lock", f"user:{username}", None, None)
            db.commit()


# --- the dependency on every guarded route ------------------------------------------------------------------


def require_unlocked(principal: AppPrincipal = Depends(require_scope("admin"))) -> AppPrincipal:
    """`principal: AppPrincipal = Depends(require_unlocked)`: super admin AND unlocked, else 403 gate_closed."""
    if principal.console_user is None:
        raise AppError(403, "gate_closed", "Only a person logged in to the console can do this, not an API key.")
    if not status(principal.console_user)["unlocked_until"]:
        raise AppError(403, "gate_closed", f"Unlock with your security password first (unlocks for {UNLOCK_MINUTES} minutes).")
    return principal
