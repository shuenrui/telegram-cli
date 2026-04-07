"""Configuration management - loads from .env or environment variables."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv


def _config_dir() -> Path:
    """Return the XDG-compliant config directory for tg-cli."""
    if raw := os.environ.get("XDG_CONFIG_HOME", ""):
        return Path(raw).expanduser() / "tg-cli"
    return Path.home() / ".config" / "tg-cli"


def _load_env() -> None:
    """Load .env only from the fixed config directory (~/.config/tg-cli/.env)."""
    candidate = _config_dir() / ".env"
    if candidate.is_file():
        load_dotenv(candidate)


def _default_data_home() -> Path:
    """Return a platform-appropriate base directory for application data."""
    if raw := os.environ.get("XDG_DATA_HOME", ""):
        return Path(raw).expanduser()

    home = Path.home()
    if sys.platform == "darwin":
        return home / "Library" / "Application Support"
    if os.name == "nt":
        local_appdata = os.environ.get("LOCALAPPDATA", "")
        if local_appdata:
            return Path(local_appdata).expanduser()
        return home / "AppData" / "Local"
    return home / ".local" / "share"


def _resolve_env_path(raw: str) -> Path:
    """Resolve user-provided paths relative to the current working directory."""
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = Path.cwd() / path
    return path


_load_env()

APP_NAME = "tg-cli"


class MissingCredentialsError(SystemExit):
    """Raised when Telegram API credentials are not configured."""

    def __init__(self):
        super().__init__(
            "\n❌ TG_API_ID and TG_API_HASH are required.\n"
            "   1. Go to https://my.telegram.org and create an application\n"
            "   2. Set them in your environment or in ~/.config/tg-cli/.env:\n\n"
            '      TG_API_ID=12345678\n'
            '      TG_API_HASH="your_api_hash_here"\n'
        )


def get_api_id() -> int:
    val = os.environ.get("TG_API_ID", "")
    if not val:
        raise MissingCredentialsError()
    return int(val)


def get_api_hash() -> str:
    val = os.environ.get("TG_API_HASH", "")
    if not val:
        raise MissingCredentialsError()
    return val


def get_session_name() -> str:
    return os.environ.get("TG_SESSION_NAME", "tg_cli")


def get_session_path() -> str:
    """Return session file path inside data/ directory."""
    data_dir = get_data_dir()
    name = get_session_name()
    return str(data_dir / name)


def secure_file(path: Path | str) -> None:
    """Set file permissions to owner-only (600) if the file exists."""
    p = Path(path)
    if p.exists() and os.name != "nt":
        p.chmod(0o600)


def get_data_dir() -> Path:
    """Return data directory, create if not exists."""
    raw = os.environ.get("DATA_DIR", "")
    if raw:
        d = _resolve_env_path(raw)
    else:
        d = _default_data_home() / APP_NAME
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_db_path() -> Path:
    raw = os.environ.get("DB_PATH", "")
    if raw:
        p = _resolve_env_path(raw)
    else:
        p = get_data_dir() / "messages.db"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p
