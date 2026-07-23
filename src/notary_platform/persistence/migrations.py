"""Versioned schema migration runner for PostgreSQL persistence.

Replaces the unversioned ``_ensure_schema`` pattern with an idempotent,
ordered migration list. Each migration is a ``(version, description, sql)``
tuple. The runner tracks applied migrations in a ``schema_migrations`` table
and applies only those not yet recorded.
"""

from __future__ import annotations

from typing import Any

import sqlalchemy

MIGRATIONS: list[tuple[str, str, str]] = [
    (
        "001",
        "Create incidents, wo28_objects, replay_execution_events tables",
        """
        CREATE TABLE IF NOT EXISTS incidents (
            incident_id TEXT PRIMARY KEY,
            org_id TEXT NOT NULL,
            status TEXT NOT NULL,
            snapshot_summary JSONB,
            replay_result JSONB,
            mutation_result JSONB,
            certificate JSONB,
            custody JSONB,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE TABLE IF NOT EXISTS wo28_objects (
            id TEXT PRIMARY KEY,
            org_id TEXT NOT NULL,
            environment_id TEXT NOT NULL DEFAULT 'env:demo',
            kind TEXT NOT NULL,
            data JSONB NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE TABLE IF NOT EXISTS replay_execution_events (
            run_id TEXT NOT NULL,
            sequence INTEGER NOT NULL,
            step TEXT NOT NULL,
            source TEXT NOT NULL,
            expected TEXT NOT NULL,
            actual TEXT NOT NULL,
            status TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            PRIMARY KEY (run_id, sequence)
        );

        CREATE INDEX IF NOT EXISTS idx_wo28_kind_org_env
            ON wo28_objects(kind, org_id, environment_id);

        CREATE INDEX IF NOT EXISTS idx_replay_events_run_id
            ON replay_execution_events(run_id);
        """,
    ),
    (
        "002",
        "Add tenant and uniqueness indexes",
        """
        CREATE INDEX IF NOT EXISTS idx_incidents_org_id
            ON incidents(org_id);

        CREATE INDEX IF NOT EXISTS idx_wo28_org_id
            ON wo28_objects(org_id);

        CREATE INDEX IF NOT EXISTS idx_wo28_kind
            ON wo28_objects(kind);

        CREATE UNIQUE INDEX IF NOT EXISTS idx_wo28_id_kind
            ON wo28_objects(id, kind);
        """,
    ),
]


def get_applied_versions(engine: sqlalchemy.Engine) -> set[str]:
    """Return the set of migration versions already applied."""
    with engine.connect() as conn:
        try:
            rows = conn.exec_driver_sql(
                "SELECT version FROM schema_migrations ORDER BY version"
            ).mappings().all()
            return {r["version"] for r in rows}
        except Exception:
            return set()


def ensure_migration_tracker(engine: sqlalchemy.Engine) -> None:
    """Create the ``schema_migrations`` tracking table if it does not exist."""
    with engine.begin() as conn:
        conn.exec_driver_sql(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version TEXT PRIMARY KEY,
                description TEXT NOT NULL,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )


def run_migrations(engine: sqlalchemy.Engine) -> list[dict[str, Any]]:
    """Apply all unapplied migrations and return the list of applied versions."""
    ensure_migration_tracker(engine)
    applied = get_applied_versions(engine)
    results: list[dict[str, Any]] = []

    with engine.begin() as conn:
        for version, description, sql in MIGRATIONS:
            if version in applied:
                continue
            for statement in sql.strip().split(";"):
                stmt = statement.strip()
                if stmt:
                    conn.exec_driver_sql(stmt)
            conn.exec_driver_sql(
                "INSERT INTO schema_migrations (version, description) VALUES (%(v)s, %(d)s)",
                {"v": version, "d": description},
            )
            results.append({"version": version, "description": description})

    return results
