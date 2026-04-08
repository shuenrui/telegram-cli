# tg-cli

[![CI](https://github.com/shuenrui/telegram-cli/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/shuenrui/telegram-cli/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)

Hardened, agent-ready Telegram CLI built on Telethon. Syncs messages into a local SQLite cache so AI agents and humans can query the same data without hitting Telegram on every call.

Forked from [jackwener/tg-cli](https://github.com/jackwener/tg-cli) and extended with security hardening, audit logging, rate limiting, read-only mode, and multi-account isolation for production AI agent use.

---

## What's inside

- **Local-first** — sync once, query many times from SQLite
- **Agent-friendly** — structured `--json` / `--yaml` output on every command
- **Read-only by default** — send/edit/delete are disabled unless explicitly opted in
- **Audit logging** — every CLI invocation is recorded to a local `audit.db`
- **Rate limit budget** — token bucket per rolling hour, configurable, blocks at exhaustion
- **Chat allowlist** — restrict `send` to a whitelist of numeric chat IDs
- **Multi-account** — isolated data dirs per account via `--account`
- **Honest device fingerprint** — auto-detects OS/arch instead of hardcoding macOS values

---

## Installation

**From this fork (recommended):**

```bash
git clone git@github.com:shuenrui/telegram-cli.git
cd telegram-cli
pip install -e .
```

**Or with uv:**

```bash
uv tool install git+https://github.com/shuenrui/telegram-cli.git
```

**Requirements:** Python 3.10+

---

## Authentication

tg-cli uses your personal Telegram account over MTProto — not the Bot API.

**Step 1 — Get API credentials:**

Go to [my.telegram.org](https://my.telegram.org), create an application, and note the `api_id` and `api_hash`.

**Step 2 — Create the config file:**

```bash
mkdir -p ~/.config/tg-cli
cat > ~/.config/tg-cli/.env <<EOF
TG_API_ID=your_api_id
TG_API_HASH=your_api_hash
TG_MODE=readonly
EOF
chmod 600 ~/.config/tg-cli/.env
```

**Step 3 — First login (interactive, one-time only):**

```bash
tg status
# Enter your phone number and the verification code Telegram sends
```

This creates a session file in your data directory. All subsequent calls are non-interactive.

---

## Quick Start

```bash
# Check auth
tg status

# Sync everything
tg sync-all

# Browse today's messages
tg today

# Search
tg search "token launch" --hours 24

# Real-time listener
tg listen --persist
```

---

## Command Reference

### Syncing

| Command | Description |
|---------|-------------|
| `tg sync-all` | Sync all Telegram dialogs in one pass |
| `tg refresh` | Same as sync-all; shows which chats had new messages |
| `tg sync <chat>` | Incremental sync for one chat (only fetches new messages) |
| `tg history <chat> -n 1000` | Full fetch (non-incremental) up to N messages |
| `tg listen [chats...]` | Real-time listener — stores new messages as they arrive |
| `tg listen --persist` | Auto-reconnects if the connection drops |

Options for `sync-all` / `refresh`:
- `--delay 2.0` — seconds between each chat sync (anti-ban, default 1.0 with ±20% jitter)
- `--max-chats 50` — limit chats per run

### Querying (always read from local cache)

| Command | Description |
|---------|-------------|
| `tg search <keyword>` | Keyword or regex (`--regex`) search |
| `tg recent` | Latest messages |
| `tg today` | Today's messages grouped by chat |
| `tg filter <kw1,kw2,...>` | OR-logic multi-keyword filter |
| `tg stats` | Message count per chat |
| `tg top` | Most active senders |
| `tg timeline` | Activity over time (`--by day` or `--by hour`) |

Common query options: `-c/--chat`, `-s/--sender`, `--hours`, `-n/--limit`, `--sync-first`

### Account & Chat Info

| Command | Description |
|---------|-------------|
| `tg chats` | List all joined chats. Filter with `--type user\|group\|channel` |
| `tg info <chat>` | Detailed info: ID, type, member count, description |
| `tg whoami` | Current logged-in user |
| `tg status` | Authentication status check |

### Writing (requires `TG_MODE=readwrite`)

These are **disabled by default**. Set `TG_MODE=readwrite` to enable.

| Command | Description |
|---------|-------------|
| `tg send <chat> <message>` | Send a message. Respects `TG_SEND_ALLOWLIST` |
| `tg edit <chat> <msg_id> <new_text>` | Edit one of your messages |
| `tg delete <chat> <msg_id...>` | Delete one or more messages |

### Data Management

| Command | Description |
|---------|-------------|
| `tg export <chat>` | Export messages to text/JSON/YAML. `-o` to write to file |
| `tg purge <chat>` | Delete all locally stored messages for a chat (`-y` skips confirm) |

---

## Global Flags

| Flag | Description |
|------|-------------|
| `--account <name>` | Switch account context (default: `default`) |
| `-v / --verbose` | Enable debug logging |
| `--json` | Machine-readable JSON output |
| `--yaml` | Machine-readable YAML output (preferred for agents) |
| `--version` | Show installed version |

---

## Structured Output

All commands support `--json` and `--yaml`. When stdout is not a TTY, YAML is the default. Use `OUTPUT=yaml|json|rich|auto` to override.

**Success envelope:**
```yaml
ok: true
schema_version: "1"
data: ...
```

**Error envelope:**
```yaml
ok: false
schema_version: "1"
error:
  code: chat_not_found
  message: "Chat 'foo' not found in database."
```

Full schema: [SCHEMA.md](./SCHEMA.md)

---

## Security Features

### Read-only mode (default)

`TG_MODE=readonly` is the default. The `send`, `edit`, and `delete` commands exit immediately with a clear error unless `TG_MODE=readwrite` is set. All read commands (sync, search, today, listen, etc.) are always allowed.

```bash
# Enable write access explicitly
export TG_MODE=readwrite
tg send "MyGroup" "Hello"
```

### Chat allowlist

Restrict `send` to a fixed set of chat IDs. If the target is not in the list, the command refuses before any message is sent.

```bash
export TG_SEND_ALLOWLIST="-1001234567890,-1009876543210"
tg send "MyGroup" "Hello"   # works only if MyGroup's ID is in the list
```

Leave unset to allow sending to any chat (backward-compatible default).

### Audit logging

Every CLI command invocation is recorded to `audit.db` in the data directory (chmod 600).

Schema: `id | timestamp | action | target_chat | parameters (JSON) | caller`

```bash
# Inspect the audit log directly
sqlite3 ~/Library/Application\ Support/tg-cli/audit.db \
  "SELECT timestamp, action, parameters FROM audit_log ORDER BY id DESC LIMIT 20;"
```

### Rate limit budget

A rolling-hour token bucket prevents API abuse. Each `sync`, `sync-all`, and `send` call consumes one token.

```bash
export TG_RATE_LIMIT_HOURLY=60   # default
```

- At 80% consumption: warning printed to stderr
- At 100%: call is blocked, caller falls back to cached data
- Budget stored in `ratelimit.db` (chmod 600)

### Honest device fingerprint

The client reports the actual host OS and architecture (`platform.machine()`, `platform.system()`, `platform.release()`) and the installed package version instead of hardcoded `macOS 15.3 / Telegram Desktop 5.12.1`. This avoids Telegram anti-fraud flags when the session IP doesn't match a macOS geolocation.

---

## Multi-Account Support

Each account gets its own isolated subdirectory with its own session file, `messages.db`, `audit.db`, and `ratelimit.db`.

```bash
# Use a named account
tg --account=research sync-all
tg --account=research search "IDO launch" --json

tg --account=ops send "AlertsChannel" "Deploy complete"

# Default account (no flag) — uses existing top-level data dir, backward-compatible
tg sync-all
```

Account data lives at: `<data_dir>/accounts/<name>/`

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `TG_API_ID` | — | **Required.** Telegram app ID from my.telegram.org |
| `TG_API_HASH` | — | **Required.** Telegram app hash |
| `TG_MODE` | `readonly` | `readonly` or `readwrite`. Controls send/edit/delete access |
| `TG_SEND_ALLOWLIST` | unset | Comma-separated numeric chat IDs allowed for `send` |
| `TG_RATE_LIMIT_HOURLY` | `60` | Max API calls per rolling hour |
| `TG_SESSION_NAME` | `tg_cli` | Session file name |
| `DATA_DIR` | platform default | Override the data directory path |
| `DB_PATH` | `<data_dir>/messages.db` | Override the messages DB path |
| `OUTPUT` | `auto` | Default output format: `yaml`, `json`, `rich`, `auto` |
| `XDG_CONFIG_HOME` | `~/.config` | Override config directory base |
| `XDG_DATA_HOME` | platform default | Override data directory base |

**Platform data directory defaults:**

| OS | Path |
|----|------|
| macOS | `~/Library/Application Support/tg-cli/` |
| Linux | `~/.local/share/tg-cli/` |
| Windows | `%LOCALAPPDATA%\tg-cli\` |

Config file (credentials, env vars): `~/.config/tg-cli/.env`

---

## AI Agent Integration

tg-cli is designed to be called as a subprocess tool by AI agents. All output is machine-readable and the exit code is reliable (0 = success, non-zero = failure).

### Basic agent tool wrapper (Python)

```python
import subprocess
import json

def tg(cmd: list[str]) -> dict:
    result = subprocess.run(
        ["tg"] + cmd + ["--json"],
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)

# Examples
tg(["search", "IDO launch", "--hours", "24"])
tg(["today"])
tg(["recent", "--chat", "CryptoAlpha", "--hours", "6"])
tg(["filter", "token,launch,TGE", "--hours", "48"])
```

### Recommended agent workflow

```bash
# 1. Keep cache fresh with a cron (agents read from cache, not live Telegram)
*/15 * * * *  tg --account=research sync-all --max-chats 50

# 2. Agent queries (fast, no Telegram API calls)
tg --account=research search "IDO" --hours 24 --json
tg --account=research today --json
tg --account=research filter "airdrop,whitelist,mint" --hours 12 --json
tg --account=research top --hours 24 --json
```

### Multi-agent setup

Give each agent its own account name so rate budgets and audit logs are isolated:

```bash
tg --account=research-agent search "DeFi" --json
tg --account=alpha-agent today --json
tg --account=monitor-agent listen --persist
```

### Use cases

**Crypto research / signal extraction**
```bash
# Find IDO announcements in the last 24h
tg search "IDO" --hours 24 --json

# Top senders in alpha groups this week
tg top --chat "CryptoAlpha" --hours 168 --json

# Activity timeline to spot announcement spikes
tg timeline --chat "ProjectAnnouncements" --by hour --json
```

**Monitoring and alerting**
```bash
# Keep a near-real-time cache of specific chats
tg listen "AlertsChannel" "PriceBot" --persist

# Pull recent alerts for agent processing
tg recent --chat "AlertsChannel" --hours 1 --json
```

**Research export**
```bash
# Export a full channel's history for offline analysis
tg sync "ResearchChannel" -n 10000
tg export "ResearchChannel" -f json -o research.json

# Export last 7 days to YAML for LLM context
tg export "ResearchChannel" --hours 168 -f yaml -o context.yaml
```

**Multi-account operations**
```bash
# Separate read account for research vs write account for ops
tg --account=research sync-all
tg --account=ops send "OpsChannel" "Task complete"
```

---

## Scheduling

### cron

```bash
# Sync all chats every 15 minutes, max 50 chats per run
*/15 * * * *  tg sync-all --max-chats 50 >> ~/.local/share/tg-cli/sync.log 2>&1

# Full refresh once a day at 6am
0 6 * * *     tg refresh >> ~/.local/share/tg-cli/refresh.log 2>&1
```

See [`examples/tg-refresh.cron`](https://github.com/shuenrui/telegram-cli/blob/main/examples/tg-refresh.cron).

### systemd user timer

```bash
mkdir -p ~/.config/systemd/user
cp examples/systemd/tg-refresh.service ~/.config/systemd/user/
cp examples/systemd/tg-refresh.timer ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now tg-refresh.timer
```

See:
- [`examples/systemd/tg-refresh.service`](https://github.com/shuenrui/telegram-cli/blob/main/examples/systemd/tg-refresh.service)
- [`examples/systemd/tg-refresh.timer`](https://github.com/shuenrui/telegram-cli/blob/main/examples/systemd/tg-refresh.timer)

---

## Account Safety

tg-cli uses your personal Telegram account via MTProto. To reduce the risk of account restrictions:

1. **Use your own API credentials** — the default shared credentials attract stricter Telegram scrutiny
2. **Keep sync frequency low** — avoid `sync-all` more than a few times per hour; use `--max-chats` to spread load
3. **Use `--delay`** — both `refresh` and `sync-all` support `--delay 2.0` to pace requests
4. **Prefer established accounts** — new accounts are flagged more aggressively
5. **Keep write operations minimal** — `send` carries significantly more risk than read commands; use `TG_MODE=readonly` (the default) unless you explicitly need to send

---

## Known Security Limitations

- **`edit` is not covered by `TG_SEND_ALLOWLIST`** — only `send` is currently allowlist-gated
- **`TG_MODE` is a soft control** — any process with access to the environment can override it
- **Plaintext message storage** — messages are stored unencrypted in SQLite; protect the data directory
- **`--account` names are not sanitised** — avoid special characters or path separators in account names
- **`purge` has no mode guard** — it deletes local rows and is not blocked by readonly mode

---

## Troubleshooting

**`No messages today`**
Run `tg refresh` first, or use `tg today --sync-first`.

**`Chat '...' not found in database`**
Run `tg sync-all` first to populate the cache, or use the numeric `chat_id` from `tg chats --json`.

**`Rate budget exhausted`**
Too many API calls in the past hour. Wait, or increase `TG_RATE_LIMIT_HOURLY`.

**`FloodWaitError`**
Telegram is rate-limiting your account. The CLI will wait automatically, but reduce `--max-chats` and increase `--delay` if it happens often.

**Debug logging**
```bash
tg -v sync-all      # shows request timing, entity resolution, DB writes
tg -v search "foo"  # shows SQL queries
```

---

## License

Apache-2.0
