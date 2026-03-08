"""tg-cli — Telegram CLI entry point."""

import click

from .data import data_group
from .query import query_group
from .tg import tg_group


@click.group()
@click.version_option(package_name="tg-cli")
def cli():
    """tg — Telegram CLI for monitoring chats, searching messages, and AI analysis."""
    pass


# Register sub-groups
cli.add_command(tg_group, "tg")

# Register top-level query commands
for name, cmd in query_group.commands.items():
    cli.add_command(cmd, name)

# Register top-level data commands
for name, cmd in data_group.commands.items():
    cli.add_command(cmd, name)
