"""CLI entry helpers."""

from __future__ import annotations

from src.interfaces.commands import CommandContext, handle_command


def run_cli(context: CommandContext) -> None:
    """Run a simple interactive CLI loop."""
    print("Terrarium observer CLI")
    print("Type 'help' for commands.")
    print(f"Snapshot: {context.snapshot_path}")

    while True:
        try:
            raw_command = input("> ")
        except EOFError:
            print()
            break
        except KeyboardInterrupt:
            print()
            break

        output = handle_command(context, raw_command)
        if output == "__QUIT__":
            break
        if output:
            print(output)
