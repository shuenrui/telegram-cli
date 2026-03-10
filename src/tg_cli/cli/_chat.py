"""Shared chat resolution helpers for CLI commands."""

from rich.table import Table

from ..console import console
from ..db import MessageDB


def resolve_chat_id_or_print(
    db: MessageDB,
    chat: str | None,
    *,
    allow_missing: bool = False,
) -> int | None:
    """Resolve a user-supplied chat filter and print helpful errors."""
    if not chat:
        return None

    matches = db.find_chats(chat)
    if not matches:
        if allow_missing:
            return None
        console.print(f"[red]Chat '{chat}' not found in database.[/red]")
        return None

    if len(matches) == 1:
        return matches[0]["chat_id"]

    table = Table(title=f"Ambiguous chat: {chat}")
    table.add_column("Chat ID", style="dim")
    table.add_column("Chat Name", style="bold")
    table.add_column("Messages", justify="right")
    for match in matches[:10]:
        table.add_row(
            str(match["chat_id"]),
            match.get("chat_name") or "—",
            str(match.get("msg_count") or 0),
        )

    console.print(f"[red]Chat '{chat}' matches multiple local chats.[/red]")
    console.print(table)
    console.print("[yellow]Use a more specific name or the numeric chat ID.[/yellow]")
    return None
