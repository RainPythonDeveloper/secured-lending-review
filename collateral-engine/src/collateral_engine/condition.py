"""Status of the declared condition, set by the versioned rules in config/condition_rules.yaml."""

from collections import Counter
from dataclasses import dataclass

from collateral_engine.domain import ClaimStatus, Condition
from collateral_engine.policy import ConditionRules
from collateral_engine.report import ConditionVerification
from collateral_engine.vision import PhotoAssessment, VisionConfidence

CONFIDENCE_ORDER = (VisionConfidence.LOW, VisionConfidence.MEDIUM, VisionConfidence.HIGH)


@dataclass(frozen=True)
class ObservedCondition:
    condition: Condition | None
    counted_photos: int
    agreement_share: float | None


def counts_towards_condition(assessment: PhotoAssessment, rules: ConditionRules) -> bool:
    is_confident_enough = CONFIDENCE_ORDER.index(assessment.confidence) >= CONFIDENCE_ORDER.index(
        VisionConfidence(rules.min_confidence)
    )
    return (
        assessment.shows_apartment_interior
        and not assessment.contains_people
        and assessment.observed_condition is not None
        and is_confident_enough
    )


def observe_condition(
    assessments: list[PhotoAssessment], rules: ConditionRules
) -> ObservedCondition:
    """The most frequent condition, only if enough photos agree on it."""
    counted = [
        assessment.observed_condition
        for assessment in assessments
        if counts_towards_condition(assessment, rules)
    ]
    if not counted:
        return ObservedCondition(None, 0, None)
    most_common, votes = Counter(counted).most_common(1)[0]
    agreement_share = votes / len(counted)
    is_settled = (
        len(counted) >= rules.min_classified_photos and agreement_share >= rules.min_agreement_share
    )
    return ObservedCondition(
        most_common if is_settled else None, len(counted), round(agreement_share, 4)
    )


def condition_status(
    declared: Condition, observed: ObservedCondition, photo_count: int, rules: ConditionRules
) -> ClaimStatus:
    if photo_count == 0:
        return ClaimStatus.NOT_VERIFIED
    if observed.condition is None:
        return ClaimStatus.INCONCLUSIVE
    gap = abs(rules.finish_levels[declared] - rules.finish_levels[observed.condition])
    if gap <= rules.verified_max_gap:
        return ClaimStatus.VERIFIED
    if gap <= rules.partly_max_gap:
        return ClaimStatus.PARTLY
    return ClaimStatus.CONTRADICTED


def verify_condition(
    declared: Condition,
    assessments: list[PhotoAssessment],
    photo_count: int,
    rules: ConditionRules,
) -> ConditionVerification:
    """When the photos disagree with the declaration, the flat is valued as the photos show it."""
    observed = observe_condition(assessments, rules)
    status = condition_status(declared, observed, photo_count, rules)
    disagrees = status in (ClaimStatus.PARTLY, ClaimStatus.CONTRADICTED)
    valued_condition = observed.condition if disagrees and observed.condition else declared
    return ConditionVerification(
        declared=declared,
        observed=observed.condition,
        status=status,
        valued_condition=valued_condition,
        counted_photos=observed.counted_photos,
        agreement_share=observed.agreement_share,
        photos_submitted=photo_count,
        photos_required=rules.min_photos,
        rules_version=rules.version,
    )
