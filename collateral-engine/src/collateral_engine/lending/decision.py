"""The loan officer's decision on an assessed application, written to the audit log.

The pipeline only recommends. A decision that differs from the recommendation, and every
decline, needs a written reason; the recommendation is read back from the audit log, not taken
from the caller.
"""

from decimal import Decimal
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from collateral_engine.audit import AuditEvent, AuditLog, ReasonRequiredError
from collateral_engine.lending.pipeline import LendingRecommendation


class LoanDecisionKind(StrEnum):
    APPROVE = "APPROVE"
    APPROVE_REDUCED = "APPROVE_REDUCED"
    REQUEST_DOCUMENTS = "REQUEST_DOCUMENTS"
    DECLINE = "DECLINE"


# The decision that follows each recommendation without a written reason.
EXPECTED_DECISION = {
    LendingRecommendation.OFFER: LoanDecisionKind.APPROVE,
    LendingRecommendation.OFFER_REDUCED: LoanDecisionKind.APPROVE_REDUCED,
    LendingRecommendation.OFFICER_REVIEW: LoanDecisionKind.REQUEST_DOCUMENTS,
    LendingRecommendation.COMPLIANCE_REVIEW: LoanDecisionKind.REQUEST_DOCUMENTS,
    LendingRecommendation.PHYSICAL_INSPECTION: LoanDecisionKind.REQUEST_DOCUMENTS,
}


class UnknownApplicationError(LookupError):
    """No assessment of this application is in the audit log."""


class LoanDecision(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    application_id: str
    officer_id: Annotated[str, Field(min_length=1, max_length=64)]
    decision: LoanDecisionKind
    amount_gel: Annotated[Decimal, Field(ge=0)]
    reason: Annotated[str, Field(max_length=2000)] = ""


def record_loan_decision(audit_log: AuditLog, decision: LoanDecision) -> str:
    assessed = audit_log.find_latest(
        AuditEvent.LOAN_APPLICATION_ASSESSED, "application_id", decision.application_id
    )
    if assessed is None:
        raise UnknownApplicationError(
            f"application {decision.application_id} is not in the audit log"
        )
    recommendation = LendingRecommendation(assessed["recommendation"])
    is_against = decision.decision is not EXPECTED_DECISION[recommendation]
    needs_reason = is_against or decision.decision is LoanDecisionKind.DECLINE
    if needs_reason and not decision.reason.strip():
        raise ReasonRequiredError(
            f"the system recommended {recommendation}; deciding {decision.decision} needs a reason"
        )
    return audit_log.append(
        {
            "event": AuditEvent.LOAN_DECISION,
            "recommendation": recommendation,
            "is_against_recommendation": is_against,
            **decision.model_dump(mode="json"),
        }
    )
