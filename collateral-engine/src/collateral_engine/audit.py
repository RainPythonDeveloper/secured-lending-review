"""Append-only audit log in which each record carries the hash of the previous one.

Changing or deleting a past record breaks the chain, and verify() reports it. Valuations store the
SHA-256 of every evidence photo, so the photos the officer saw can be proven later.
"""

import hashlib
import json
import sqlite3
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from collateral_engine.flags import Recommendation
from collateral_engine.report import ValuationReport
from collateral_engine.vehicles.report import VehicleValuationReport

GENESIS_HASH = "0" * 64


class AuditEvent(StrEnum):
    VALUATION_ASSESSED = "valuation_assessed"
    FULL_APPLICATION_ASSESSED = "full_application_assessed"
    LOAN_APPLICATION_ASSESSED = "loan_application_assessed"
    OFFICER_DECISION = "officer_decision"
    LOAN_DECISION = "loan_decision"
    LIVENESS_CHECKED = "liveness_checked"


class OfficerDecisionKind(StrEnum):
    ACCEPT_VALUATION = "ACCEPT_VALUATION"
    PHYSICAL_INSPECTION = "PHYSICAL_INSPECTION"


class OfficerDecision(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    valuation_id: str
    officer_id: Annotated[str, Field(min_length=1, max_length=64)]
    decision: OfficerDecisionKind
    reason: Annotated[str, Field(max_length=2000)] = ""


class ReasonRequiredError(ValueError):
    """The officer decided against the recommendation without a written reason."""


class UnknownValuationError(LookupError):
    """No valuation with this id is in the audit log."""


class AuditRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    sequence: int
    recorded_at: str
    record_hash: str
    payload: dict


class AuditLog:
    def __init__(self, path: Path) -> None:
        self._path = path
        with sqlite3.connect(self._path) as connection:
            connection.execute(
                """CREATE TABLE IF NOT EXISTS audit_log(
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    recorded_at TEXT NOT NULL,
                    previous_hash TEXT NOT NULL,
                    record_hash TEXT NOT NULL UNIQUE,
                    payload TEXT NOT NULL)"""
            )

    @staticmethod
    def _digest(previous_hash: str, recorded_at: str, payload: str) -> str:
        return hashlib.sha256(f"{previous_hash}|{recorded_at}|{payload}".encode()).hexdigest()

    def append(self, payload: dict) -> str:
        serialised = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
        recorded_at = datetime.now(UTC).isoformat(timespec="seconds")
        with sqlite3.connect(self._path) as connection:
            last = connection.execute(
                "SELECT record_hash FROM audit_log ORDER BY sequence DESC LIMIT 1"
            ).fetchone()
            previous_hash = last[0] if last else GENESIS_HASH
            record_hash = self._digest(previous_hash, recorded_at, serialised)
            connection.execute(
                "INSERT INTO audit_log(recorded_at, previous_hash, record_hash, payload) "
                "VALUES (?, ?, ?, ?)",
                (recorded_at, previous_hash, record_hash, serialised),
            )
        return record_hash

    def recent(self, limit: int = 50) -> list[AuditRecord]:
        with sqlite3.connect(self._path) as connection:
            rows = connection.execute(
                "SELECT sequence, recorded_at, record_hash, payload FROM audit_log "
                "ORDER BY sequence DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [
            AuditRecord(
                sequence=sequence,
                recorded_at=recorded_at,
                record_hash=record_hash,
                payload=json.loads(payload),
            )
            for sequence, recorded_at, record_hash, payload in rows
        ]

    def verify(self) -> tuple[bool, int]:
        """Whether the chain is intact, and how many records were checked."""
        with sqlite3.connect(self._path) as connection:
            rows = connection.execute(
                "SELECT recorded_at, previous_hash, record_hash, payload FROM audit_log "
                "ORDER BY sequence"
            ).fetchall()
        expected_previous = GENESIS_HASH
        for recorded_at, previous_hash, record_hash, payload in rows:
            if previous_hash != expected_previous:
                return False, len(rows)
            if self._digest(previous_hash, recorded_at, payload) != record_hash:
                return False, len(rows)
            expected_previous = record_hash
        return True, len(rows)

    def find_latest(self, event: "AuditEvent", field: str, value: str) -> dict | None:
        """The most recent record of the event whose field has the value."""
        with sqlite3.connect(self._path) as connection:
            rows = connection.execute(
                "SELECT payload FROM audit_log ORDER BY sequence DESC"
            ).fetchall()
        for (payload,) in rows:
            record = json.loads(payload)
            if record.get("event") == event and record.get(field) == value:
                return record
        return None

    def records_of(self, event: "AuditEvent", field: str, value: str) -> list[AuditRecord]:
        """Every record of the event whose field has the value, oldest first."""
        with sqlite3.connect(self._path) as connection:
            rows = connection.execute(
                "SELECT sequence, recorded_at, record_hash, payload FROM audit_log "
                "ORDER BY sequence"
            ).fetchall()
        records = [
            AuditRecord(
                sequence=sequence,
                recorded_at=recorded_at,
                record_hash=record_hash,
                payload=json.loads(payload),
            )
            for sequence, recorded_at, record_hash, payload in rows
        ]
        return [
            record
            for record in records
            if record.payload.get("event") == event and record.payload.get(field) == value
        ]

    def find_valuation(self, valuation_id: str) -> dict:
        with sqlite3.connect(self._path) as connection:
            rows = connection.execute("SELECT payload FROM audit_log ORDER BY sequence").fetchall()
        for (payload,) in rows:
            record = json.loads(payload)
            is_valuation = record["event"] == AuditEvent.VALUATION_ASSESSED
            if is_valuation and record["valuation_id"] == valuation_id:
                return record
        raise UnknownValuationError(f"valuation {valuation_id} is not in the audit log")


def record_valuation(audit_log: AuditLog, report: ValuationReport | VehicleValuationReport) -> str:
    report_json = report.model_dump_json()
    return audit_log.append(
        {
            "event": AuditEvent.VALUATION_ASSESSED,
            "valuation_id": report.valuation_id,
            "application_id": report.application_id,
            "recommendation": report.recommendation,
            "report_sha256": hashlib.sha256(report_json.encode()).hexdigest(),
            "photo_sha256": [photo.sha256 for photo in report.photos],
            "report": json.loads(report_json),
        }
    )


def record_officer_decision(audit_log: AuditLog, decision: OfficerDecision) -> str:
    """A decision that differs from the recommendation needs a written reason."""
    valuation = audit_log.find_valuation(decision.valuation_id)
    recommendation = Recommendation(valuation["recommendation"])
    if decision.decision.value != recommendation.value and not decision.reason.strip():
        raise ReasonRequiredError(
            f"the system recommended {recommendation}; deciding {decision.decision} needs a reason"
        )
    return audit_log.append(
        {
            "event": AuditEvent.OFFICER_DECISION,
            "recommendation": recommendation,
            **decision.model_dump(mode="json"),
        }
    )
