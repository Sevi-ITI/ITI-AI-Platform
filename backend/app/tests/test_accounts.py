"""Console accounts: password hashing and creating an account (6A.1a part 1)."""

import pytest
from pydantic import ValidationError

from app.auth.b_models.console_user import ConsoleUser
from app.auth.d_keys.hash_password import hash_password
from app.auth.d_keys.password_matches import password_matches
from app.console.a_schemas.account_create import AccountCreate
from app.console.d_service.create_account import create_account
from app.core.c_database.get_sessionmaker import get_sessionmaker
from app.core.e_errors.app_error import AppError

PASSWORD = "correct horse battery"
VINCE = {"username": "vince", "role": "super_admin", "password": PASSWORD}


def test_a_password_is_salted_and_only_its_own_password_matches():
    first, second = hash_password(PASSWORD), hash_password(PASSWORD)
    assert first.startswith("scrypt$16384$8$5$") and first != second  # a new salt every time
    assert PASSWORD not in first
    assert password_matches(PASSWORD, first) and password_matches(PASSWORD, second)
    assert not password_matches("correct horse battery!", first)
    for damaged in ("", "sha256$abc", first.replace("scrypt", "bcrypt"), first[:-6] + "!!!!!!"):
        assert not password_matches(PASSWORD, damaged)


def test_create_an_account_stores_only_the_hash_and_refuses_a_taken_name(db_engine):
    with get_sessionmaker()() as db:
        info = create_account(db, AccountCreate(**VINCE, display_name="Vince"))
        assert (info.username, info.role, info.active, info.last_login_at) == ("vince", "super_admin", True, None)
        row = db.get(ConsoleUser, "vince")
        assert row.password_hash.startswith("scrypt$") and PASSWORD not in row.password_hash
        assert password_matches(PASSWORD, row.password_hash) and row.failed_logins == 0
        with pytest.raises(AppError) as taken:
            create_account(db, AccountCreate(**VINCE | {"role": "supervisor"}))
        assert (taken.value.status, taken.value.code) == (409, "account_exists")


@pytest.mark.parametrize(
    "bad",
    [{"username": "Vince"}, {"username": "vi"}, {"username": "vince ok"}, {"role": "admin"}, {"password": "short pw"}],
    ids=["upper", "too-short", "space", "role", "password"],
)
def test_bad_accounts_are_refused_without_echoing_the_password(bad):
    with pytest.raises(ValidationError) as refused:
        AccountCreate(**VINCE | bad)
    assert PASSWORD not in str(refused.value) and "short pw" not in str(refused.value)
