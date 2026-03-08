# tg-cli

Telegram CLI — monitor group chats, search messages, AI analysis.

Uses your own Telegram account (MTProto), not a Bot. Built-in API credentials — just install and login.

## Quick Start

```bash
# Install
pip install tg-cli
# or
uv tool install tg-cli

# Login (first run) — enter phone + verification code
tg tg chats

# Sync all groups at once
tg tg sync-all

# See today's messages
tg today

# Search
tg search "Rust"
```

## Commands

### Telegram (`tg tg ...`)

| Command | Description |
|---------|-------------|
| `tg chats [--type group]` | List joined chats |
| `tg history CHAT -n 1000` | Fetch historical messages |
| `tg sync CHAT` | Incremental sync (only new messages) |
| `tg sync-all` | Sync ALL chats in database (single connection) |
| `tg listen [CHATS...]` | Real-time listener |
| `tg info CHAT` | Show detailed chat info |

### Query

| Command | Description |
|---------|-------------|
| `search KEYWORD [-c NAME] [--json]` | Search stored messages |
| `stats` | Show message statistics |
| `top [-c NAME] [--hours 24]` | Most active senders |
| `timeline [-c NAME] [--by day\|hour]` | Message activity bar chart |
| `today [-c NAME] [--json]` | Show today's messages by chat |

### Data & AI

| Command | Description |
|---------|-------------|
| `export CHAT [-f text\|json] [-o FILE] [--hours N]` | Export messages |
| `purge CHAT [-y]` | Delete stored messages |
| `analyze CHAT [--hours 24] [-p PROMPT]` | AI analysis (Claude) |
| `summary [-c NAME] [--hours N]` | AI daily digest |

## Setup

```bash
pip install tg-cli  # or: uv tool install tg-cli
tg tg chats         # login with phone number
```

That's it. Built-in API credentials work for most users.

**Optional:**
- Custom API credentials: set `TG_API_ID` and `TG_API_HASH` env vars
- AI analysis: `pip install tg-cli[ai]` + set `ANTHROPIC_AUTH_TOKEN`
- Custom data dir: `DATA_DIR=./data` or `DB_PATH=./data/messages.db`

## Architecture

```
src/tg_cli/
├── cli/
│   ├── main.py      # Click CLI entry point
│   ├── tg.py        # Telegram: chats, sync, sync-all, listen
│   ├── query.py     # Query: search, stats, today, top, timeline
│   └── data.py      # Data: export, purge, analyze, summary
├── client.py        # Telethon client (connection reuse)
├── config.py        # Config (built-in API credentials)
├── db.py            # SQLite message store
└── analyzer.py      # Claude AI analysis
```

## License

MIT
