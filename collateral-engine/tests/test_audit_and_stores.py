import hashlib
import sqlite3
from pathlib import Path

import pytest

from collateral_engine.audit import (
    AuditLog,
    OfficerDecision,
    OfficerDecisionKind,
    ReasonRequiredError,
    UnknownValuationError,
    record_officer_decision,
)
from collateral_engine.evidence import EvidenceStore
from collateral_engine.photo_registry import PhotoRegistry


def valuation_record(valuation_id: str, recommendation: str) -> dict:
    return {
        "event": "valuation_assessed",
        "valuation_id": valuation_id,
        "recommendation": recommendation,
    }


def decision(kind: OfficerDecisionKind, reason: str = "") -> OfficerDecision:
    return OfficerDecision(valuation_id="V-1", officer_id="officer-7", decision=kind, reason=reason)


def test_intact_chain_verifies(tmp_path: Path) -> None:
    audit_log = AuditLog(tmp_path / "audit.db")
    audit_log.append({"event": "valuation_assessed", "valuation_id": "V-1"})
    audit_log.append({"event": "officer_decision", "valuation_id": "V-1"})

    assert audit_log.verify() == (True, 2)


def test_edited_record_breaks_the_chain(tmp_path: Path) -> None:
    database = tmp_path / "audit.db"
    audit_log = AuditLog(database)
    audit_log.append({"event": "valuation_assessed", "valuation_id": "V-1"})
    audit_log.append({"event": "officer_decision", "valuation_id": "V-1"})
    with sqlite3.connect(database) as connection:
        connection.execute("UPDATE audit_log SET payload = '{}' WHERE sequence = 1")

    assert audit_log.verify() == (False, 2)


def test_deleted_record_breaks_the_chain(tmp_path: Path) -> None:
    database = tmp_path / "audit.db"
    audit_log = AuditLog(database)
    for valuation_id in ("V-1", "V-2", "V-3"):
        audit_log.append({"event": "valuation_assessed", "valuation_id": valuation_id})
    with sqlite3.connect(database) as connection:
        connection.execute("DELETE FROM audit_log WHERE sequence = 2")

    assert audit_log.verify() == (False, 2)


def test_decision_following_recommendation_needs_no_reason(tmp_path: Path) -> None:
    audit_log = AuditLog(tmp_path / "audit.db")
    audit_log.append(valuation_record("V-1", "ACCEPT_VALUATION"))

    record_officer_decision(audit_log, decision(OfficerDecisionKind.ACCEPT_VALUATION))

    assert audit_log.recent(1)[0].payload["decision"] == "ACCEPT_VALUATION"


@pytest.mark.parametrize("recommendation", ["OFFICER_REVIEW", "PHYSICAL_INSPECTION"])
def test_accepting_against_recommendation_needs_reason(tmp_path: Path, recommendation: str) -> None:
    audit_log = AuditLog(tmp_path / "audit.db")
    audit_log.append(valuation_record("V-1", recommendation))

    with pytest.raises(ReasonRequiredError):
        record_officer_decision(audit_log, decision(OfficerDecisionKind.ACCEPT_VALUATION, "  "))


def test_decision_against_recommendation_with_reason_is_recorded(tmp_path: Path) -> None:
    audit_log = AuditLog(tmp_path / "audit.db")
    audit_log.append(valuation_record("V-1", "OFFICER_REVIEW"))

    record_officer_decision(
        audit_log,
        decision(OfficerDecisionKind.ACCEPT_VALUATION, "Valuer confirmed renovation on site"),
    )

    record = audit_log.recent(1)[0].payload
    assert (record["recommendation"], record["reason"]) == (
        "OFFICER_REVIEW",
        "Valuer confirmed renovation on site",
    )


def test_decision_on_unknown_valuation_is_refused(tmp_path: Path) -> None:
    audit_log = AuditLog(tmp_path / "audit.db")

    with pytest.raises(UnknownValuationError):
        record_officer_decision(audit_log, decision(OfficerDecisionKind.ACCEPT_VALUATION))


def test_registry_finds_similar_photo_from_other_application(tmp_path: Path) -> None:
    registry = PhotoRegistry(tmp_path / "audit.db")
    registry.register("APP-1", "a" * 64, 0b1111_0000)

    assert registry.applications_with_similar_photo(0b1111_0001, 6, "APP-2") == ["APP-1"]


def test_registry_ignores_same_application(tmp_path: Path) -> None:
    registry = PhotoRegistry(tmp_path / "audit.db")
    registry.register("APP-1", "a" * 64, 0b1111_0000)

    assert registry.applications_with_similar_photo(0b1111_0000, 6, "APP-1") == []


def test_registry_keeps_full_64_bit_hashes(tmp_path: Path) -> None:
    registry = PhotoRegistry(tmp_path / "audit.db")
    top_bit_hash = 1 << 63
    registry.register("APP-1", "b" * 64, top_bit_hash)

    assert registry.applications_with_similar_photo(top_bit_hash, 0, "APP-2") == ["APP-1"]


def test_evidence_is_stored_under_its_sha256_once(tmp_path: Path) -> None:
    store = EvidenceStore(tmp_path / "evidence")
    content = b"photo bytes"
    sha256 = hashlib.sha256(content).hexdigest()

    first = store.save(sha256, content)
    second = store.save(sha256, b"different bytes must not overwrite evidence")

    assert first == second
    assert store.load(sha256) == content


def test_evidence_store_rejects_path_like_names(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="SHA-256"):
        EvidenceStore(tmp_path).path_for("../../etc/passwd")
