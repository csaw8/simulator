"""Application entry point for the terrarium prototype."""

from __future__ import annotations

import sys

from src.app.bootstrap import bootstrap_command_context
from src.interfaces.cli import run_cli
from src.interfaces.commands import handle_command


def main() -> None:
    """Start the terrarium observer CLI or run a one-shot command."""
    bootstrap = bootstrap_command_context()
    context = bootstrap.context

    if len(sys.argv) > 1:
        command = " ".join(sys.argv[1:])
        output = handle_command(context, command)
        if output and output != "__QUIT__":
            print(output)
        return

    run_cli(context)


if __name__ == "__main__":
    main()
