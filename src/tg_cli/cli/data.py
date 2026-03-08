"""Data commands — export, purge, analyze, summary."""

import json

import click
from rich.console import Console

from ..db import MessageDB

console = Console()


@click.group("data", invoke_without_command=True)
def data_group():
    """Data management commands (registered at top-level)."""
    pass


@data_group.command("export")
@click.argument("chat")
@click.option("-f", "--format", "fmt", type=click.Choice(["text", "json"]), default="text")
@click.option("-o", "--output", "output_file", help="Output file path")
@click.option("--hours", type=int, help="Only export last N hours")
def export(chat: str, fmt: str, output_file: str | None, hours: int | None):
    """Export messages from CHAT to text or JSON."""
    db = MessageDB()
    chat_id = db.resolve_chat_id(chat)

    if chat_id is None:
        console.print(f"[red]Chat '{chat}' not found in database.[/red]")
        db.close()
        return

    if hours:
        msgs = db.get_recent(chat_id=chat_id, hours=hours, limit=100000)
    else:
        msgs = db.get_recent(chat_id=chat_id, hours=None, limit=100000)
    db.close()

    if not msgs:
        console.print(f"[yellow]No messages found for '{chat}'.[/yellow]")
        return

    if fmt == "json":
        content = json.dumps(msgs, ensure_ascii=False, indent=2, default=str)
    else:
        lines = []
        for msg in msgs:
            ts = (msg.get("timestamp") or "")[:19]
            sender = msg.get("sender_name") or "Unknown"
            text = msg.get("content") or ""
            lines.append(f"[{ts}] {sender}: {text}")
        content = "\n".join(lines)

    if output_file:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(content)
        console.print(f"[green]✓[/green] Exported {len(msgs)} messages to {output_file}")
    else:
        console.print(content)


@data_group.command("purge")
@click.argument("chat")
@click.option("-y", "--yes", is_flag=True, help="Skip confirmation")
def purge(chat: str, yes: bool):
    """Delete all stored messages for CHAT."""
    db = MessageDB()
    chat_id = db.resolve_chat_id(chat)

    if chat_id is None:
        console.print(f"[red]Chat '{chat}' not found in database.[/red]")
        db.close()
        return

    if not yes:
        count = db.count(chat_id)
        if not click.confirm(f"Delete {count} messages from chat {chat_id}?"):
            db.close()
            return

    deleted = db.delete_chat(chat_id)
    db.close()
    console.print(f"[green]✓[/green] Deleted {deleted} messages")


@data_group.command("analyze")
@click.argument("chat")
@click.option("--hours", type=int, default=24, help="Analyze last N hours")
@click.option("-p", "--prompt", help="Custom analysis prompt")
def analyze(chat: str, hours: int, prompt: str | None):
    """Analyze chat messages with AI (Claude)."""
    from ..analyzer import analyze_messages

    db = MessageDB()
    chat_id = db.resolve_chat_id(chat)

    if chat_id is None:
        console.print(f"[red]Chat '{chat}' not found.[/red]")
        db.close()
        return

    # Get chat name
    chats = db.get_chats()
    chat_name = next((c["chat_name"] for c in chats if c["chat_id"] == chat_id), chat)

    msgs = db.get_recent(chat_id=chat_id, hours=hours)
    db.close()

    if not msgs:
        console.print(f"[yellow]No messages in last {hours}h.[/yellow]")
        return

    console.print(f"[dim]Analyzing {len(msgs)} messages from {chat_name}...[/dim]")
    result = analyze_messages(msgs, prompt=prompt, chat_name=chat_name)
    console.print(result)


@data_group.command("summary")
@click.option("-c", "--chat", help="Filter by chat name (default: all chats)")
@click.option("--hours", type=int, help="Summarize last N hours (default: today)")
def summary(chat: str | None, hours: int | None):
    """AI summary of today's messages (or last N hours)."""
    from collections import defaultdict

    from ..analyzer import analyze_messages

    db = MessageDB()

    if hours:
        chat_id = db.resolve_chat_id(chat) if chat else None
        msgs = db.get_recent(chat_id=chat_id, hours=hours)
    else:
        chat_id = db.resolve_chat_id(chat) if chat else None
        msgs = db.get_today(chat_id=chat_id)

    db.close()

    if not msgs:
        console.print("[yellow]No messages to summarize.[/yellow]")
        return

    # Group by chat for a multi-chat summary
    grouped: dict[str, list[dict]] = defaultdict(list)
    for m in msgs:
        grouped[m.get("chat_name") or "Unknown"].append(m)

    console.print(f"[dim]Summarizing {len(msgs)} messages from {len(grouped)} chats...[/dim]")

    # Build a combined prompt
    parts = []
    for chat_name, chat_msgs in sorted(grouped.items(), key=lambda x: -len(x[1])):
        parts.append(f"\n### {chat_name} ({len(chat_msgs)} 条)")
        for m in chat_msgs:
            ts = (m.get("timestamp") or "")[:19]
            sender = m.get("sender_name") or "Unknown"
            content = m.get("content") or ""
            parts.append(f"[{ts}] {sender}: {content}")

    combined_prompt = f"""请总结以下 {len(grouped)} 个 Telegram 群组的消息：

1. **每个群的核心话题** — 简明扼要
2. **值得关注的信息** — 有价值的链接、项目、工具、招聘
3. **整体概览** — 今天社区的整体讨论趋势

请用中文回答，按群组分别总结，保持简洁有深度。"""

    result = analyze_messages(
        msgs,
        prompt=combined_prompt,
    )
    console.print(result)
