"""Token-bucket rate limiter backed by SQLite.

Each API call (sync, send) consumes one token from an hourly budget.
At 80 % consumption a warning is printed. When the budget is exhausted
the call is blocked and callers fall back to cache-only reads.

Configuration
-------------
TG_RATE_LIMIT_HOURLY  int  Max API calls per rolling hour (default: 60)
"""

from __future__ import annotations

import logging
import os
import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path

from .config import get_data_dir, secure_file
from .console import console

log = logging.getLogger(__name__)

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS rate_events (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp        TEXT    NOT NULL,
    action           TEXT    NOT NULL,
    tokens_consumed  INTEGER NOT NULL DEFAULT 1,
    tokens_remaining INTEGER NOT NULL
)
"""

_WARN_THRESHOLD = 0.80  # warn when >= 80 % of budget used


def _ratelimit_db_path() -> Path:
    return get_data_dir() / "ratelimit.db"


def _hourly_limit() -> int:
    try:
        return int(os.environ.get("TG_RATE_LIMIT_HOURLY", "60"))
    except ValueError:
        return 60


class RateLimiter:
    """Token-bucket rate limiter.  One instance per process; cheap to create."""

    def __init__(self) -> None:
        path = _ratelimit_db_path()
        self._conn = sqlite3.connect(path)
        self._conn.execute(_CREATE_TABLE)
        self._conn.commit()
        secure_file(path)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _used_in_window(self) -> int:
        """Count tokens consumed in the past rolling hour."""
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        row = self._conn.execute(
            "SELECT COALESCE(SUM(tokens_consumed), 0) FROM rate_events WHERE timestamp > ?",
            (cutoff,),
        ).fetchone()
        return int(row[0]) if row else 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def check(self, action: str) -> bool:
        """Consume one token for *action*.

        Returns True if the call is allowed, False if the budget is
        exhausted (caller should fall back to cache).  Prints a warning
        when usage crosses the 80 % threshold.
        """
        limit = _hourly_limit()
        used = self._used_in_window()

        if used >= limit:
            console.print(
                f"[red]✗ Rate budget exhausted ({used}/{limit} calls in the past hour). "
                "Falling back to cached data. Try again later.[/red]"
            )
            return False

        remaining_after = limit - used - 1

        self._conn.execute(
            "INSERT INTO rate_events (timestamp, action, tokens_consumed, tokens_remaining)"
            " VALUES (?, ?, 1, ?)",
            (datetime.now(timezone.utc).isoformat(), action, remaining_after),
        )
        self._conn.commit()

        # Warn once when crossing 80 %
        if (used + 1) / limit >= _WARN_THRESHOLD:
            console.print(
                f"[yellow]⚠ Rate budget at {used + 1}/{limit} calls this hour "
                f"({remaining_after} remaining).[/yellow]"
            )

        return True

    def close(self) -> None:
        self._conn.close()


# ---------------------------------------------------------------------------
# Convenience context manager
# ---------------------------------------------------------------------------

class rate_check:  # noqa: N801  — intentionally lowercase for readability
    """Context manager that checks the rate budget before an action.

    Usage::

        with rate_check("sync") as allowed:
            if allowed:
                await fetch_history(...)
            else:
                # fall back to DB-only result
                ...
    """

    def __init__(self, action: str) -> None:
        self._action = action
        self._limiter: RateLimiter | None = None
        self.allowed = True

    def __enter__(self) -> "rate_check":
        try:
            self._limiter = RateLimiter()
            self.allowed = self._limiter.check(self._action)
        except Exception as exc:
            log.debug("Rate limiter error (allowing call): %s", exc)
            self.allowed = True
        return self

    def __exit__(self, *_) -> None:
        if self._limiter:
            try:
                self._limiter.close()
            except Exception:
                pass
