"""Audit logging — records every CLI command invocation to a local SQLite DB."""

from __future__ import annotations

import json
import logging
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .config import get_data_dir, secure_file

log = logging.getLogger(__name__)

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS audit_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp   TEXT    NOT NULL,
    action      TEXT    NOT NULL,
    target_chat TEXT,
    parameters  TEXT,
    caller      TEXT
)
"""


def _audit_db_path() -> Path:
    return get_data_dir() / "audit.db"


def _caller() -> str:
    try:
        return os.getlogin()
    except Exception:
        return os.environ.get("USER", os.environ.get("USERNAME", "unknown"))


class AuditLogger:
    """Thin wrapper around the audit SQLite DB."""

    def __init__(self) -> None:
        path = _audit_db_path()
        self._conn = sqlite3.connect(path)
        self._conn.execute(_CREATE_TABLE)
        self._conn.commit()
        secure_file(path)

    def log(
        self,
        action: str,
        *,
        target_chat: str | None = None,
        parameters: dict | None = None,
    ) -> None:
        try:
            self._conn.execute(
                "INSERT INTO audit_log"
                " (timestamp, action, target_chat, parameters, caller)"
                " VALUES (?, ?, ?, ?, ?)",
                (
                    datetime.now(timezone.utc).isoformat(),
                    action,
                    target_chat,
                    json.dumps(parameters) if parameters is not None else None,
                    _caller(),
                ),
            )
            self._conn.commit()
        except Exception as exc:
            log.debug("Audit log write failed: %s", exc)

    def close(self) -> None:
        self._conn.close()


def log_command(action: str, args: list[str]) -> None:
    """Log a CLI command invocation. Silently ignores failures so audit never breaks the CLI."""
    try:
        logger = AuditLogger()
        logger.log(action=action, parameters={"args": args})
        logger.close()
    except Exception as exc:
        log.debug("Audit logging failed: %s", exc)
