"""tg-cli — Telegram CLI entry point."""

import logging
import sys

import click

from .data import data_group
from .query import query_group
from .tg import tg_group


def _setup_logging(verbose: bool):
    level = logging.DEBUG if verbose else logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )


class _AuditGroup(click.Group):
    """click.Group subclass that audit-logs every subcommand invocation."""

    def invoke(self, ctx: click.Context) -> object:
        # protected_args[0] is the subcommand name after group options are parsed
        subcmd = ctx.protected_args[0] if ctx.protected_args else None
        if subcmd:
            try:
                from ..audit import log_command

                log_command(subcmd, sys.argv[1:])
            except Exception:
                pass  # audit must never break the CLI
        return super().invoke(ctx)


@click.group(cls=_AuditGroup)
@click.version_option(package_name="kabi-tg-cli")
@click.option("-v", "--verbose", is_flag=True, help="Enable debug logging")
def cli(verbose: bool):
    """tg — Telegram CLI for syncing chats, searching messages, and local analysis."""
    _setup_logging(verbose)


# Register ALL commands at top-level (flat structure, no `tg tg` nonsense)
for group in (tg_group, query_group, data_group):
    for name, cmd in group.commands.items():
        cli.add_command(cmd, name)
