import pytest

from builders import assessment
from collateral_engine.condition import (
    counts_towards_condition,
    observe_condition,
    verify_condition,
)
from collateral_engine.domain import ClaimStatus, Condition
from collateral_engine.policy import ConditionRules
from collateral_engine.vision import VisionConfidence


@pytest.mark.parametrize(
    ("declared", "observed", "status"),
    [
        (Condition.NEWLY_RENOVATED, Condition.NEWLY_RENOVATED, ClaimStatus.VERIFIED),
        (Condition.GREEN_FRAME, Condition.NEEDS_RENOVATION, ClaimStatus.VERIFIED),
        (Condition.NEWLY_RENOVATED, Condition.OLD_RENOVATED, ClaimStatus.PARTLY),
        (Condition.WHITE_FRAME, Condition.BLACK_FRAME, ClaimStatus.PARTLY),
        (Condition.NEWLY_RENOVATED, Condition.WHITE_FRAME, ClaimStatus.CONTRADICTED),
        (Condition.NEWLY_RENOVATED, Condition.BLACK_FRAME, ClaimStatus.CONTRADICTED),
    ],
)
def test_status_follows_finish_level_gap(
    condition_rules: ConditionRules, declared: Condition, observed: Condition, status: ClaimStatus
) -> None:
    photos = [assessment(observed)] * 3

    assert verify_condition(declared, photos, len(photos), condition_rules).status is status


def test_no_photos_leaves_condition_not_verified(condition_rules: ConditionRules) -> None:
    verification = verify_condition(Condition.NEWLY_RENOVATED, [], 0, condition_rules)

    assert verification.status is ClaimStatus.NOT_VERIFIED
    assert verification.valued_condition is Condition.NEWLY_RENOVATED


def test_one_assessed_photo_is_inconclusive(condition_rules: ConditionRules) -> None:
    photos = [assessment(Condition.BLACK_FRAME)]

    verification = verify_condition(Condition.NEWLY_RENOVATED, photos, 3, condition_rules)

    assert verification.status is ClaimStatus.INCONCLUSIVE


def test_photos_that_disagree_are_inconclusive(condition_rules: ConditionRules) -> None:
    photos = [assessment(Condition.BLACK_FRAME), assessment(Condition.NEWLY_RENOVATED)]

    verification = verify_condition(Condition.NEWLY_RENOVATED, photos, 2, condition_rules)

    assert verification.status is ClaimStatus.INCONCLUSIVE
    assert verification.agreement_share == 0.5


def test_unassessed_photos_never_contradict(condition_rules: ConditionRules) -> None:
    verification = verify_condition(Condition.NEWLY_RENOVATED, [], 4, condition_rules)

    assert verification.status is ClaimStatus.INCONCLUSIVE


def test_contradicted_flat_is_valued_as_photos_show(condition_rules: ConditionRules) -> None:
    photos = [assessment(Condition.WHITE_FRAME)] * 3

    verification = verify_condition(Condition.NEWLY_RENOVATED, photos, 3, condition_rules)

    assert verification.valued_condition is Condition.WHITE_FRAME


@pytest.mark.parametrize(
    "photo",
    [
        assessment(Condition.BLACK_FRAME, contains_people=True),
        assessment(Condition.BLACK_FRAME, shows_apartment_interior=False),
        assessment(Condition.BLACK_FRAME, confidence=VisionConfidence.LOW),
        assessment("undetermined"),
    ],
)
def test_photo_that_cannot_count_is_ignored(condition_rules: ConditionRules, photo) -> None:
    assert not counts_towards_condition(photo, condition_rules)


def test_observation_requires_agreement_share(condition_rules: ConditionRules) -> None:
    photos = [assessment(Condition.WHITE_FRAME)] * 2 + [assessment(Condition.BLACK_FRAME)]

    observed = observe_condition(photos, condition_rules)

    assert (observed.condition, observed.counted_photos) == (Condition.WHITE_FRAME, 3)


def test_verification_records_rules_version(condition_rules: ConditionRules) -> None:
    verification = verify_condition(Condition.NEWLY_RENOVATED, [], 0, condition_rules)

    assert verification.rules_version == condition_rules.version


def test_two_agreeing_photos_are_not_enough(condition_rules: ConditionRules) -> None:
    photos = [assessment(Condition.NEWLY_RENOVATED)] * 2

    verification = verify_condition(Condition.NEWLY_RENOVATED, photos, 2, condition_rules)

    assert verification.status is ClaimStatus.INCONCLUSIVE


def test_three_agreeing_photos_verify_the_condition(condition_rules: ConditionRules) -> None:
    photos = [assessment(Condition.NEWLY_RENOVATED)] * 3

    verification = verify_condition(Condition.NEWLY_RENOVATED, photos, 3, condition_rules)

    assert verification.status is ClaimStatus.VERIFIED


def test_verification_reports_submitted_and_required_photos(
    condition_rules: ConditionRules,
) -> None:
    verification = verify_condition(Condition.NEWLY_RENOVATED, [], 2, condition_rules)

    assert (verification.photos_submitted, verification.photos_required) == (
        2,
        condition_rules.min_photos,
    )
