"""SQLite export and query helpers.

SQLite is a derived query layer. JSON snapshots remain the authoritative state.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from dataclasses import asdict
from pathlib import Path

from src.world.state import WorldState

DEFAULT_SQLITE_PATH = Path("data/world_ledger.sqlite3")


def export_world_to_sqlite(world: WorldState, path: Path = DEFAULT_SQLITE_PATH) -> None:
    """Export current world state into a compact SQLite query database."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(path)) as conn:
        with conn:
            _create_schema(conn)
            _clear_export_tables(conn)
            _insert_events(conn, world)
            _insert_relations(conn, world)
            _insert_dynamic_structures(conn, world)
            _insert_emergent_presences(conn, world)
            _insert_ai_proposal_audits(conn, world)


def sqlite_stats(path: Path = DEFAULT_SQLITE_PATH) -> dict[str, int]:
    """Return table counts from an exported SQLite database."""
    if not path.exists():
        return {}
    tables = [
        "events",
        "relations",
        "dynamic_structures",
        "emergent_presences",
        "ai_proposal_audits",
    ]
    with closing(sqlite3.connect(path)) as conn:
        return {
            table: int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
            for table in tables
        }


def format_sqlite_stats(path: Path = DEFAULT_SQLITE_PATH) -> str:
    """Render SQLite export stats for CLI output."""
    stats = sqlite_stats(path)
    if not stats:
        return f"SQLite export not found: {path}"
    lines = [f"SQLite stats: {path}"]
    for key in [
        "events",
        "relations",
        "dynamic_structures",
        "emergent_presences",
        "ai_proposal_audits",
    ]:
        lines.append(f"  {key}: {stats.get(key, 0)}")
    return "\n".join(lines)


def _create_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS events (
            event_id TEXT PRIMARY KEY,
            tick INTEGER NOT NULL,
            event_type TEXT NOT NULL,
            event_scope TEXT NOT NULL,
            severity TEXT NOT NULL,
            visibility TEXT NOT NULL,
            summary TEXT NOT NULL,
            payload_json TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS relations (
            relation_id TEXT PRIMARY KEY,
            source_ref TEXT NOT NULL,
            target_ref TEXT NOT NULL,
            relation_type TEXT NOT NULL,
            strength TEXT NOT NULL,
            status TEXT NOT NULL,
            updated_tick INTEGER NOT NULL,
            payload_json TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS dynamic_structures (
            structure_id TEXT PRIMARY KEY,
            structure_type TEXT NOT NULL,
            status TEXT NOT NULL,
            pressure TEXT NOT NULL,
            visibility TEXT NOT NULL,
            updated_tick INTEGER NOT NULL,
            payload_json TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS emergent_presences (
            presence_id TEXT PRIMARY KEY,
            presence_type TEXT NOT NULL,
            status TEXT NOT NULL,
            lifecycle_stage TEXT NOT NULL,
            pressure TEXT NOT NULL,
            visibility TEXT NOT NULL,
            updated_tick INTEGER NOT NULL,
            payload_json TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS ai_proposal_audits (
            audit_id TEXT PRIMARY KEY,
            tick INTEGER NOT NULL,
            proposal_type TEXT NOT NULL,
            target_type TEXT NOT NULL,
            target_id TEXT NOT NULL,
            mode TEXT NOT NULL,
            source TEXT NOT NULL,
            applied INTEGER NOT NULL,
            signal_score INTEGER NOT NULL,
            payload_json TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_events_tick ON events(tick);
        CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type);
        CREATE INDEX IF NOT EXISTS idx_relations_refs ON relations(source_ref, target_ref);
        CREATE INDEX IF NOT EXISTS idx_audits_type ON ai_proposal_audits(proposal_type);
        """
    )


def _clear_export_tables(conn: sqlite3.Connection) -> None:
    for table in [
        "events",
        "relations",
        "dynamic_structures",
        "emergent_presences",
        "ai_proposal_audits",
    ]:
        conn.execute(f"DELETE FROM {table}")


def _insert_events(conn: sqlite3.Connection, world: WorldState) -> None:
    conn.executemany(
        """
        INSERT INTO events (
            event_id, tick, event_type, event_scope, severity, visibility, summary, payload_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                event.event_id,
                event.tick,
                event.event_type,
                event.event_scope,
                event.severity,
                event.visibility,
                event.summary,
                _json(asdict(event)),
            )
            for event in world.event_stream.events
        ],
    )


def _insert_relations(conn: sqlite3.Connection, world: WorldState) -> None:
    conn.executemany(
        """
        INSERT INTO relations (
            relation_id, source_ref, target_ref, relation_type, strength, status, updated_tick, payload_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                relation.relation_id,
                relation.source_ref,
                relation.target_ref,
                relation.relation_type,
                relation.strength,
                relation.status,
                relation.updated_tick,
                _json(asdict(relation)),
            )
            for relation in world.relations.values()
        ],
    )


def _insert_dynamic_structures(conn: sqlite3.Connection, world: WorldState) -> None:
    conn.executemany(
        """
        INSERT INTO dynamic_structures (
            structure_id, structure_type, status, pressure, visibility, updated_tick, payload_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                structure.structure_id,
                structure.structure_type,
                structure.status,
                structure.pressure,
                structure.visibility,
                structure.updated_tick,
                _json(asdict(structure)),
            )
            for structure in world.dynamic_structures.values()
        ],
    )


def _insert_emergent_presences(conn: sqlite3.Connection, world: WorldState) -> None:
    conn.executemany(
        """
        INSERT INTO emergent_presences (
            presence_id, presence_type, status, lifecycle_stage, pressure, visibility, updated_tick, payload_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                presence.presence_id,
                presence.presence_type,
                presence.status,
                presence.lifecycle_stage,
                presence.pressure,
                presence.visibility,
                presence.updated_tick,
                _json(asdict(presence)),
            )
            for presence in world.emergent_presences.values()
        ],
    )


def _insert_ai_proposal_audits(conn: sqlite3.Connection, world: WorldState) -> None:
    conn.executemany(
        """
        INSERT INTO ai_proposal_audits (
            audit_id, tick, proposal_type, target_type, target_id, mode, source, applied, signal_score, payload_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                audit.audit_id,
                audit.tick,
                audit.proposal_type,
                audit.target_type,
                audit.target_id,
                audit.mode,
                audit.source,
                1 if audit.applied else 0,
                audit.signal_score,
                _json(asdict(audit)),
            )
            for audit in world.ai_proposal_audits.values()
        ],
    )


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)
