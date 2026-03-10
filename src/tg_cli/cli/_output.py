"""Shared structured output helpers for CLI commands."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

import click
import yaml


def structured_output_options(command: Callable) -> Callable:
    """Add --json/--yaml flags to a click command."""
    command = click.option("--yaml", "as_yaml", is_flag=True, help="Output as YAML")(command)
    command = click.option("--json", "as_json", is_flag=True, help="Output as JSON")(command)
    return command


def emit_structured(data: Any, *, as_json: bool, as_yaml: bool) -> bool:
    """Emit structured output and return True when a structured format was used."""
    if not as_json and not as_yaml:
        return False

    if as_json and as_yaml:
        raise click.UsageError("Use only one of --json or --yaml.")

    click.echo(dump_structured(data, fmt="json" if as_json else "yaml"))
    return True


def dump_structured(data: Any, *, fmt: str) -> str:
    """Serialize structured data to JSON or YAML text."""
    if fmt == "json":
        return json.dumps(data, ensure_ascii=False, indent=2, default=str)
    if fmt == "yaml":
        return yaml.safe_dump(
            data,
            allow_unicode=True,
            sort_keys=False,
            default_flow_style=False,
        )
    raise ValueError(f"Unsupported structured format: {fmt}")
