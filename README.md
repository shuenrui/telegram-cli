# tg-cli

[![CI](https://github.com/jackwener/tg-cli/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/jackwener/tg-cli/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/kabi-tg-cli)](https://pypi.org/project/kabi-tg-cli/)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)

Telethon-powered Telegram CLI for local-first sync, search, export, and agent-friendly retrieval.

It uses your own Telegram account over MTProto, not the Bot API. Messages are synced into local SQLite,
so humans and AI agents can query the same cache quickly with `--json` or `--yaml`.

## Features

- Sync Telegram dialogs into a local SQLite cache
- Search by keyword or regex, with chat, sender, and time filters
- Browse recent messages, today's messages, top senders, and timelines
- Export messages as text, JSON, or YAML
- Keep a near-real-time cache with `tg listen --persist`
- Prefer YAML for AI agents when a strict JSON parser is not required

## Installation

```bash
# Install from PyPI
uv tool install kabi-tg-cli

# Or: pipx / pip
pipx install kabi-tg-cli
pip install kabi-tg-cli
```

Install from GitHub:

```bash
uv tool install git+https://github.com/jackwener/tg-cli.git
```

Install from source:

```bash
git clone git@github.com:jackwener/tg-cli.git
cd tg-cli
uv sync --extra dev
```

## Quick Start

```bash

# Configure credentials first
export TG_API_ID=123456
export TG_API_HASH=your_telegram_app_hash
# Or create a .env file with the same variables

# Login (first run) — enter phone + verification code
tg chats

# Check who you are
tg whoami

# Refresh local cache from all current dialogs
tg refresh

# See today's messages
tg today

# Search
tg search "Rust"
tg search "Rust" --sender "Alice" --hours 48
tg search "Rust|Golang" --regex --hours 72
tg recent --hours 24 --limit 20 --yaml
tg search "Rust" --sync-first --yaml

# Filter by keywords (comma-separated, OR logic)
tg filter "Rust,Golang,Java" --hours 48 --sync-first

# Keep a near-real-time local cache
tg listen --persist

# Send a message
tg send "GroupName" "Hello!"
```

## Why This Exists

`tg-cli` is intentionally local-first:

- `tg refresh`, `tg sync`, `tg sync-all`, and `tg listen` ingest data from Telegram
- `today`, `recent`, `search`, `filter`, `stats`, `top`, and `timeline` read from local SQLite

That makes repeated analysis fast, scriptable, and suitable for AI agents. If you need fresh data right
before a query, use `--sync-first`.

## Commands

### Telegram (`tg ...`)

| Command | Description |
|---------|-------------|
| `tg chats [--type group] [--json\|--yaml]` | List joined chats |
| `tg whoami [--json\|--yaml]` | Show current user info |
| `tg history CHAT -n 1000` | Fetch historical messages |
| `tg sync CHAT` | Incremental sync (only new messages) |
| `tg sync-all [--json\|--yaml]` | Low-level sync for all current dialogs |
| `tg refresh [--json\|--yaml]` | Recommended daily refresh entrypoint |
| `tg listen [CHATS...] [--persist]` | Real-time listener with optional auto-reconnect |
| `tg info CHAT [--json\|--yaml]` | Show detailed chat info |
| `tg send CHAT "msg"` | Send a message |

### Query

| Command | Description |
|---------|-------------|
| `search KEYWORD [-c NAME] [-s SENDER] [--hours N] [--regex] [--sync-first] [--json\|--yaml]` | Search stored messages with chat/sender/time filters or regex |
| `recent [-c NAME] [-s SENDER] [--hours N] [-n LIMIT] [--sync-first] [--json\|--yaml]` | Browse recent messages without a keyword |
| `filter KEYWORDS [-c NAME] [--hours N] [--sync-first] [--json\|--yaml]` | Multi-keyword filter (OR logic, highlighted) |
| `stats [--sync-first] [--json\|--yaml]` | Show message statistics |
| `top [-c NAME] [--hours 24] [--sync-first] [--json\|--yaml]` | Most active senders |
| `timeline [-c NAME] [--by day\|hour] [--sync-first] [--json\|--yaml]` | Message activity bar chart |
| `today [-c NAME] [--sync-first] [--json\|--yaml]` | Show today's messages by chat |


| Command | Description |
|---------|-------------|
| `export CHAT [-f text\|json\|yaml] [-o FILE] [--hours N]` | Export messages |
| `purge CHAT [-y]` | Delete stored messages |

### Global Options

| Option | Description |
|--------|-------------|
| `-v, --verbose` | Enable debug logging |
| `--version` | Show version |

## Setup

```bash
uv tool install kabi-tg-cli  # or: pip install kabi-tg-cli
# Set TG_API_ID and TG_API_HASH in your shell or a .env file
tg chats
```

After that, tg-cli stores your session locally and reuses it.

**Required:**
- Set `TG_API_ID` and `TG_API_HASH` in your environment or `.env`

**Optional:**
- Custom data dir: `DATA_DIR=./data` or `DB_PATH=./data/messages.db`
- Custom session file name: `TG_SESSION_NAME=my_session`

Apply for your own Telegram app credentials at [my.telegram.org/apps](https://my.telegram.org/apps).

## Refresh Modes

`tg-cli` is local-first: `search`, `recent`, `today`, `filter`, `stats`, `top`, and `timeline`
read from the local SQLite cache, not directly from Telegram.

- `tg refresh` is the recommended daily command. It refreshes all current dialogs and prints a short summary.
- `tg sync-all` is the lower-level primitive if you want explicit control in scripts.
- `--sync-first` is available on query commands when you want fresh data before reading.
- `tg listen --persist` keeps reconnecting automatically and is the closest thing to a live cache.

Examples:

```bash
tg refresh
tg today --sync-first --yaml
tg top --hours 24 --sync-first
tg listen --persist --retry-seconds 5
```

## Automation Examples

If you do not want to run `tg refresh` manually, use a scheduler.

### cron

See [examples/tg-refresh.cron](https://github.com/jackwener/tg-cli/blob/main/examples/tg-refresh.cron).

### systemd user timer

See:
- [tg-refresh.service](https://github.com/jackwener/tg-cli/blob/main/examples/systemd/tg-refresh.service)
- [tg-refresh.timer](https://github.com/jackwener/tg-cli/blob/main/examples/systemd/tg-refresh.timer)

Typical flow:

```bash
mkdir -p ~/.config/systemd/user
cp examples/systemd/tg-refresh.service ~/.config/systemd/user/
cp examples/systemd/tg-refresh.timer ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now tg-refresh.timer
```

## Manual Smoke Test

With valid `TG_API_ID`, `TG_API_HASH`, and a working local session:

```bash
tg whoami
tg refresh --yaml
tg recent --hours 24 --limit 5 --yaml
tg search "test" --hours 24 --sync-first --yaml
tg today --sync-first
```

These commands cover auth, sync, local reads, and structured output without sending messages.

## Troubleshooting

- `Missing TG_API_ID / TG_API_HASH`
  - Apply for your own app credentials at [my.telegram.org/apps](https://my.telegram.org/apps).
- `No messages today`
  - Run `tg refresh` first, or use `tg today --sync-first`.
- `Chat '...' not found in database`
  - Run `tg refresh` first, or use the numeric `chat_id` from `tg chats --yaml`.
- Repeatedly running `sync-all`
  - Prefer `tg refresh` for daily use, `--sync-first` for single queries, or `tg listen --persist` for a near-live cache.

## Architecture

```
src/tg_cli/
├── cli/
│   ├── main.py      # Click CLI entry point + verbose
│   ├── tg.py        # Telegram: chats, sync, refresh, listen, whoami, send
│   ├── query.py     # Query: search, regex, recent, filter, stats, today, top, timeline
├── client.py        # Telethon client (connection reuse)
├── config.py        # Config and required user-provided credentials
├── db.py            # SQLite message store
```

## Use as AI Agent Skill

tg-cli ships with a [`SKILL.md`](./SKILL.md) for AI agent integration.

For AI agents, prefer `--yaml` when a downstream parser does not strictly require JSON.
YAML is usually shorter than pretty-printed JSON and saves tokens while remaining structured.

Recommended agent pattern:

```bash
tg refresh --yaml
tg recent --hours 24 --sync-first --yaml
tg filter "招聘,remote" --hours 24 --sync-first --yaml
```

The recommended agent workflow is:

1. `tg refresh --yaml`
2. `tg chats --yaml`
3. `tg recent --hours 24 --sync-first --yaml`
4. `tg search "keyword" --chat "GroupName" --sync-first --yaml`

### Claude Code / Antigravity

```bash
mkdir -p .agents/skills
git clone git@github.com:jackwener/tg-cli.git .agents/skills/tg-cli
```

### OpenClaw / ClawHub

```bash
clawhub install tg-cli
```

## License

Apache-2.0
