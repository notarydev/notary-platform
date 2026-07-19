"""Storage backends for the Notary Platform.

The default backend is in-memory so the prototype runs with zero cloud setup.
When ``NOTARY_USE_REMOTE_STORAGE`` is enabled, incidents metadata are written
to PostgreSQL (via SQLAlchemy) and evidence/certificates to the immutable S3
bucket (Object Lock + versioning). Importers must never hardcode credentials;
they are read from the environment / IAM role at runtime.
"""

from __future__ import annotations

import abc
import json
import uuid
from typing import Any

from notary_platform.config import SETTINGS
from notary_platform.models import (
    Agent,
    CapturePolicy,
    Environment,
    Incident,
    Organization,
    SystemConnection,
)


class StorageBackend(abc.ABC):
    """Contract for incident/snapshot/certificate persistence."""

    @abc.abstractmethod
    def create_incident(self, snapshot_dict: dict[str, Any], org_id: str = "demo-org") -> Incident: ...

    @abc.abstractmethod
    def get_incident(self, incident_id: str) -> Incident | None: ...

    @abc.abstractmethod
    def list_incidents(self, org_id: str | None = None) -> list[Incident]: ...

    @abc.abstractmethod
    def get_snapshot(self, incident_id: str) -> dict[str, Any] | None: ...

    @abc.abstractmethod
    def update_incident(self, incident: Incident) -> None: ...

    @abc.abstractmethod
    def store_certificate(self, incident_id: str, cert: dict[str, Any]) -> None: ...

    @abc.abstractmethod
    def get_certificate(self, incident_id: str) -> dict[str, Any] | None: ...

    @abc.abstractmethod
    def persist_evidence(self, incident_id: str, kind: str, payload: dict[str, Any]) -> str:
        """Persist an evidence blob; returns a stable evidence reference."""

    # ── Platform objects (WO-64) ──

    @abc.abstractmethod
    def create_org(self, org: Organization) -> Organization: ...

    @abc.abstractmethod
    def get_org(self, org_id: str) -> Organization | None: ...

    @abc.abstractmethod
    def create_env(self, env: Environment) -> Environment: ...

    @abc.abstractmethod
    def get_env(self, env_id: str) -> Environment | None: ...

    @abc.abstractmethod
    def list_envs(self, org_id: str) -> list[Environment]: ...

    @abc.abstractmethod
    def create_agent(self, agent: Agent) -> Agent: ...

    @abc.abstractmethod
    def get_agent(self, agent_id: str) -> Agent | None: ...

    @abc.abstractmethod
    def list_agents_for_org(self, org_id: str, environment_id: str = "") -> list[Agent]: ...

    @abc.abstractmethod
    def create_system_conn(self, conn: SystemConnection) -> SystemConnection: ...

    @abc.abstractmethod
    def list_systems_for_org(self, org_id: str, environment_id: str = "") -> list[SystemConnection]: ...

    @abc.abstractmethod
    def create_policy(self, policy: CapturePolicy) -> CapturePolicy: ...

    @abc.abstractmethod
    def list_policies_for_org(self, org_id: str, environment_id: str = "") -> list[CapturePolicy]: ...


class MemoryStorage(StorageBackend):
    """In-memory repository for incidents and certificates (local/dev)."""

    def __init__(self) -> None:
        self._incidents: dict[str, Incident] = {}
        self._snapshots: dict[str, dict[str, Any]] = {}
        self._certificates: dict[str, dict[str, Any]] = {}
        self._evidence: dict[str, dict[str, Any]] = {}
        self._counter = 0
        # Platform objects (WO-64)
        self._orgs: dict[str, Organization] = {}
        self._envs: dict[str, Environment] = {}
        self._agents: dict[str, Agent] = {}
        self._systems: dict[str, SystemConnection] = {}
        self._policies: dict[str, CapturePolicy] = {}

    def create_incident(self, snapshot_dict: dict[str, Any], org_id: str = "demo-org") -> Incident:
        self._counter += 1
        incident_id = f"inc-{self._counter:06d}"
        snapshot_summary = {
            "schema_version": snapshot_dict.get("schema_version"),
            "timestamp": snapshot_dict.get("timestamp"),
            "element_count": len(snapshot_dict.get("elements", [])),
            "root_hash": snapshot_dict.get("root_hash", ""),
            "scenario_id": snapshot_dict.get("scenario_id"),
        }
        incident = Incident(incident_id=incident_id, org_id=org_id, snapshot_summary=snapshot_summary)
        self._incidents[incident_id] = incident
        self._snapshots[incident_id] = snapshot_dict
        return incident

    def get_incident(self, incident_id: str) -> Incident | None:
        return self._incidents.get(incident_id)

    def list_incidents(self, org_id: str | None = None) -> list[Incident]:
        items = list(self._incidents.values())
        if org_id is not None:
            items = [i for i in items if i.org_id == org_id]
        return items

    def get_snapshot(self, incident_id: str) -> dict[str, Any] | None:
        return self._snapshots.get(incident_id)

    def update_incident(self, incident: Incident) -> None:
        self._incidents[incident.incident_id] = incident

    def store_certificate(self, incident_id: str, cert: dict[str, Any]) -> None:
        self._certificates[incident_id] = cert

    def get_certificate(self, incident_id: str) -> dict[str, Any] | None:
        return self._certificates.get(incident_id)

    def persist_evidence(self, incident_id: str, kind: str, payload: dict[str, Any]) -> str:
        ref = f"{incident_id}/{kind}/{uuid.uuid4().hex}.json"
        self._evidence[ref] = payload
        return ref

    # ── Platform objects (WO-64) ──

    def create_org(self, org: Organization) -> Organization:
        self._orgs[org.id] = org
        return org

    def get_org(self, org_id: str) -> Organization | None:
        return self._orgs.get(org_id)

    def create_env(self, env: Environment) -> Environment:
        self._envs[env.id] = env
        return env

    def get_env(self, env_id: str) -> Environment | None:
        return self._envs.get(env_id)

    def list_envs(self, org_id: str) -> list[Environment]:
        return [e for e in self._envs.values() if e.org_id == org_id]

    def create_agent(self, agent: Agent) -> Agent:
        self._agents[agent.id] = agent
        return agent

    def get_agent(self, agent_id: str) -> Agent | None:
        return self._agents.get(agent_id)

    def list_agents_for_org(self, org_id: str, environment_id: str = "") -> list[Agent]:
        agents = [a for a in self._agents.values() if a.org_id == org_id]
        if environment_id:
            agents = [a for a in agents if a.environment_id == environment_id]
        return agents

    def create_system_conn(self, conn: SystemConnection) -> SystemConnection:
        self._systems[conn.id] = conn
        return conn

    def list_systems_for_org(self, org_id: str, environment_id: str = "") -> list[SystemConnection]:
        systems = [s for s in self._systems.values() if s.org_id == org_id]
        if environment_id:
            systems = [s for s in systems if s.environment_id == environment_id]
        return systems

    def create_policy(self, policy: CapturePolicy) -> CapturePolicy:
        self._policies[policy.id] = policy
        return policy

    def list_policies_for_org(self, org_id: str, environment_id: str = "") -> list[CapturePolicy]:
        policies = [p for p in self._policies.values() if p.org_id == org_id]
        if environment_id:
            policies = [p for p in policies if p.environment_id == environment_id]
        return policies


class PostgresS3Storage(StorageBackend):
    """PostgreSQL metadata + S3 immutable evidence storage.

    Credentials come from the environment / IAM role — never hardcoded. This
    backend is only constructed when ``NOTARY_USE_REMOTE_STORAGE`` is set.
    """

    def __init__(self) -> None:
        if not SETTINGS.database_url:
            raise RuntimeError("NOTARY_DATABASE_URL must be set for remote storage")
        if not SETTINGS.evidence_bucket:
            raise RuntimeError("NOTARY_EVIDENCE_BUCKET must be set for remote storage")
        # Imported lazily so the in-memory path never requires these packages.
        import boto3  # noqa: F401  (validated at construction)
        import sqlalchemy  # noqa: F401

        self._engine = sqlalchemy.create_engine(SETTINGS.database_url, future=True)
        self._bucket = SETTINGS.evidence_bucket
        self._prefix = SETTINGS.evidence_prefix
        self._session = boto3.session.Session()
        self._s3 = self._session.client("s3")
        self._ensure_schema()

    # -- metadata (Postgres) -------------------------------------------------
    def _ensure_schema(self) -> None:
        with self._engine.begin() as conn:
            conn.exec_driver_sql(
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
                )
                """
            )

    def _row_to_incident(self, row: dict[str, Any]) -> Incident:
        inc = Incident(
            incident_id=row["incident_id"],
            org_id=row["org_id"],
            status=__import__("notary_platform.models", fromlist=["IncidentStatus"]).IncidentStatus(
                row["status"]
            ),
            snapshot_summary=row.get("snapshot_summary") or {},
            replay_result=row.get("replay_result") or {},
            mutation_result=row.get("mutation_result") or {},
            certificate=row.get("certificate") or {},
        )
        inc.custody = [
            __import__("notary_platform.models", fromlist=["CustodyEvent"]).CustodyEvent(**c)
            for c in (row.get("custody") or [])
        ]
        return inc

    def create_incident(self, snapshot_dict: dict[str, Any], org_id: str = "demo-org") -> Incident:
        snapshot_summary = {
            "schema_version": snapshot_dict.get("schema_version"),
            "timestamp": snapshot_dict.get("timestamp"),
            "element_count": len(snapshot_dict.get("elements", [])),
            "root_hash": snapshot_dict.get("root_hash", ""),
            "scenario_id": snapshot_dict.get("scenario_id"),
        }
        incident = Incident(incident_id=self._next_id(), org_id=org_id, snapshot_summary=snapshot_summary)
        self._write_incident(incident)
        return incident

    def _next_id(self) -> str:
        with self._engine.connect() as conn:
            row = conn.exec_driver_sql(
                "SELECT COUNT(*) AS c FROM incidents"
            ).mappings().first()
        n = (row["c"] if row else 0) + 1
        return f"inc-{n:06d}"

    def _write_incident(self, incident: Incident) -> None:
        data = incident.to_dict()
        with self._engine.begin() as conn:
            conn.exec_driver_sql(
                """
                INSERT INTO incidents
                    (incident_id, org_id, status, snapshot_summary, replay_result,
                     mutation_result, certificate, custody)
                VALUES (:iid, :org, :status, :sum, :replay, :mut, :cert, :cust)
                ON CONFLICT (incident_id) DO UPDATE SET
                    status = EXCLUDED.status,
                    snapshot_summary = EXCLUDED.snapshot_summary,
                    replay_result = EXCLUDED.replay_result,
                    mutation_result = EXCLUDED.mutation_result,
                    certificate = EXCLUDED.certificate,
                    custody = EXCLUDED.custody
                """,
                {
                    "iid": incident.incident_id,
                    "org": incident.org_id,
                    "status": incident.status.value,
                    "sum": json.dumps(data["snapshot_summary"]),
                    "replay": json.dumps(data["replay_result"]),
                    "mut": json.dumps(data["mutation_result"]),
                    "cert": json.dumps(data["certificate"]),
                    "cust": json.dumps(data["custody"]),
                },
            )

    def get_incident(self, incident_id: str) -> Incident | None:
        with self._engine.connect() as conn:
            row = conn.exec_driver_sql(
                "SELECT * FROM incidents WHERE incident_id = :iid", {"iid": incident_id}
            ).mappings().first()
        return self._row_to_incident(dict(row)) if row else None

    def list_incidents(self, org_id: str | None = None) -> list[Incident]:
        with self._engine.connect() as conn:
            if org_id is not None:
                rows = conn.exec_driver_sql(
                    "SELECT * FROM incidents WHERE org_id = :org ORDER BY created_at",
                    {"org": org_id},
                ).mappings().all()
            else:
                rows = conn.exec_driver_sql(
                    "SELECT * FROM incidents ORDER BY created_at"
                ).mappings().all()
        return [self._row_to_incident(dict(r)) for r in rows]

    def get_snapshot(self, incident_id: str) -> dict[str, Any] | None:
        key = f"{self._prefix.rstrip('/')}/{incident_id}/snapshot.json"
        try:
            obj = self._s3.get_object(Bucket=self._bucket, Key=key)
            data: dict[str, Any] = json.loads(obj["Body"].read())
            return data
        except Exception:
            return None

    def update_incident(self, incident: Incident) -> None:
        self._write_incident(incident)

    def store_certificate(self, incident_id: str, cert: dict[str, Any]) -> None:
        incident = self.get_incident(incident_id)
        if incident is not None:
            incident.certificate = cert
            self._write_incident(incident)
        self.persist_evidence(incident_id, "certificate", cert)

    def get_certificate(self, incident_id: str) -> dict[str, Any] | None:
        key = f"{self._prefix.rstrip('/')}/{incident_id}/certificate.json"
        try:
            obj = self._s3.get_object(Bucket=self._bucket, Key=key)
            data: dict[str, Any] = json.loads(obj["Body"].read())
            return data
        except Exception:
            return None

    def persist_evidence(self, incident_id: str, kind: str, payload: dict[str, Any]) -> str:
        ref = f"{self._prefix.rstrip('/')}/{incident_id}/{kind}/{uuid.uuid4().hex}.json"
        self._s3.put_object(
            Bucket=self._bucket,
            Key=ref,
            Body=json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8"),
            ContentType="application/json",
        )
        return ref

    # ── Platform objects (WO-64) — Postgres stubs ──
    def create_org(self, org: Organization) -> Organization: return org
    def get_org(self, org_id: str) -> Organization | None: return None
    def create_env(self, env: Environment) -> Environment: return env
    def get_env(self, env_id: str) -> Environment | None: return None
    def list_envs(self, org_id: str) -> list[Environment]: return []
    def create_agent(self, agent: Agent) -> Agent: return agent
    def get_agent(self, agent_id: str) -> Agent | None: return None
    def list_agents_for_org(self, org_id: str, environment_id: str = "") -> list[Agent]: return []
    def create_system_conn(self, conn: SystemConnection) -> SystemConnection: return conn
    def list_systems_for_org(self, org_id: str, environment_id: str = "") -> list[SystemConnection]: return []
    def create_policy(self, policy: CapturePolicy) -> CapturePolicy: return policy
    def list_policies_for_org(self, org_id: str, environment_id: str = "") -> list[CapturePolicy]: return []


def get_storage() -> StorageBackend:
    """Return the configured storage backend (singleton per process)."""
    if SETTINGS.use_remote_storage:
        return PostgresS3Storage()
    return MemoryStorage()
