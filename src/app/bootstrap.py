"""Application bootstrap and dependency wiring."""

from __future__ import annotations

from dataclasses import dataclass

from src.config.env import load_dotenv
from src.config.loader import load_default_app_config
from src.config.models import AppConfig
from src.core.engine import WorldEngine
from src.interfaces.commands import CommandContext
from src.storage.snapshots import (
    DEFAULT_SNAPSHOT_PATH,
    load_world_state,
    save_world_state,
    snapshot_exists,
)
from src.world.builder import build_world


@dataclass(slots=True)
class BootstrapResult:
    """Bootstrapped application objects."""

    config: AppConfig
    context: CommandContext


def bootstrap_command_context() -> BootstrapResult:
    """Load environment, configuration, world state, and command context."""
    load_dotenv()
    config = load_default_app_config()

    if snapshot_exists(DEFAULT_SNAPSHOT_PATH):
        world = load_world_state(DEFAULT_SNAPSHOT_PATH)
    else:
        world = build_world(config.world.to_dict())
        save_world_state(world, DEFAULT_SNAPSHOT_PATH)

    context = CommandContext(
        engine=WorldEngine(world, ai_config=config.ai.to_dict()),
        world_config=config.world,
        ai_config=config.ai,
        snapshot_path=DEFAULT_SNAPSHOT_PATH,
    )
    return BootstrapResult(config=config, context=context)
