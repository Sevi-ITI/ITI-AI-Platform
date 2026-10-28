"""LoginThrottle: failed console logins per COMPUTER (security plan S2.1, 2026-10-28).

- 10 failed logins from one computer within 15 minutes block that computer for 15 minutes: 429 too_many_attempts,
  checked BEFORE the password, so a blocked computer costs no scrypt check (16 MiB each).
- Every failure counts (wrong password, unknown username, locked account), so trying one password on many
  accounts (spraying) is stopped too. A successful login does NOT clear the count: an attacker can't reset it by
  logging into their own account.
- The account lock (5 wrong in a row, record_failed_login) is unchanged and still applies everywhere.
- The computer is the ITI-Client-IP header that Caddy sets (post_login); "local" = no header (http://127.0.0.1:4000).
- Kept in memory: the API is one process on purpose; a restart forgets the counts (an attacker can't cause one)."""

import logging
import threading
import time
from collections import deque

from app.core.e_errors.app_error import AppError

MAX_FAILURES = 10
WINDOW_S = 15 * 60
BLOCK_S = 15 * 60

log = logging.getLogger(__name__)


class LoginThrottle:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._failures: dict[str, deque[float]] = {}  # computer -> times of its recent failures
        self._blocked_until: dict[str, float] = {}

    def check(self, computer: str) -> None:
        """Refuses a blocked computer with 429 (call before the password is checked)."""
        with self._lock:
            if self._blocked_until.get(computer, 0) > time.monotonic():
                raise AppError(429, "too_many_attempts", "Too many failed logins from this computer. Try again in 15 minutes.")

    def failed(self, computer: str) -> None:
        """Counts one failed login; the MAX_FAILURES-th within WINDOW_S blocks the computer for BLOCK_S."""
        now = time.monotonic()
        with self._lock:
            times = self._failures.setdefault(computer, deque())
            times.append(now)
            while times and times[0] <= now - WINDOW_S:
                times.popleft()
            if len(times) >= MAX_FAILURES:
                self._blocked_until[computer] = now + BLOCK_S
                times.clear()
                log.warning("console login blocked for %s min: %s failed logins from %s", BLOCK_S // 60, MAX_FAILURES, computer)

    def clear(self) -> None:
        """Forgets every count (tests)."""
        with self._lock:
            self._failures.clear()
            self._blocked_until.clear()


LOGIN_THROTTLE = LoginThrottle()  # the one throttle of this process
