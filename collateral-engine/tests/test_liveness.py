"""Remote identification by liveness tasks: task draw, status rules, frame hashes, audit log."""

import base64
import hashlib
import io
import random
from datetime import UTC, datetime, timedelta

import pytest
from PIL import Image
from pydantic import ValidationError

from collateral_engine.audit import AuditEvent
from collateral_engine.lending.liveness import (
    LivenessFrameError,
    LivenessIssue,
    LivenessSession,
    LivenessStatus,
    LivenessTask,
    TaskOutcome,
    attempts_in_last_day,
    decode_frame,
    draw_tasks,
    evaluate_session,
    record_liveness_check,
)
from collateral_engine.lending.policy import LivenessPolicy, load_lending_policy

SEED = 104
DRAWN = (LivenessTask.TURN_LEFT, LivenessTask.BLINK, LivenessTask.LOOK_UP)
CUSTOMER_ID = "CUS-001"
APPLICATION_ID = "LA-TEST-0001"
MAX_FRAME_BYTES = 200_000


@pytest.fixture(scope="module")
def policy() -> LivenessPolicy:
    return load_lending_policy().liveness


def jpeg_data_url(colour: tuple[int, int, int] = (40, 90, 160)) -> str:
    buffer = io.BytesIO()
    Image.new("RGB", (32, 24), colour).save(buffer, format="JPEG")
    return "data:image/jpeg;base64," + base64.b64encode(buffer.getvalue()).decode()


def outcome(task: LivenessTask, is_completed: bool = True) -> TaskOutcome:
    return TaskOutcome(
        task=task,
        is_completed=is_completed,
        response_ms=1800,
        frame_jpeg=jpeg_data_url() if is_completed else None,
    )


def session(**changes) -> LivenessSession:
    fields = {
        "session_id": "session-1",
        "is_camera_available": True,
        "is_model_available": True,
        "is_applicant_aligned": True,
        "frames_analysed": 240,
        "max_people_in_frame": 1,
        "outcomes": [outcome(task) for task in DRAWN],
        **changes,
    }
    return LivenessSession(**fields)


def evaluate(policy, liveness_session: LivenessSession):
    return evaluate_session(liveness_session, DRAWN, 1, policy, "2026-10")


def test_tasks_are_distinct_and_as_many_as_the_policy_asks(policy) -> None:
    tasks = draw_tasks(policy, random.Random(SEED))

    assert len(tasks) == policy.task_count
    assert len(set(tasks)) == len(tasks)


def test_same_chooser_state_draws_the_same_tasks(policy) -> None:
    assert draw_tasks(policy, random.Random(SEED)) == draw_tasks(policy, random.Random(SEED))


def test_policy_with_fewer_than_three_tasks_is_rejected(policy) -> None:
    # NBG Order 104/04 asks for at least three randomly chosen tasks.
    with pytest.raises(ValidationError):
        LivenessPolicy(**{**policy.model_dump(), "task_count": 2})


def test_all_drawn_tasks_done_passes(policy) -> None:
    check = evaluate(policy, session())

    assert check.status is LivenessStatus.PASSED
    assert check.issues == []


def test_a_missed_task_does_not_pass(policy) -> None:
    outcomes = [outcome(DRAWN[0]), outcome(DRAWN[1], is_completed=False), outcome(DRAWN[2])]

    check = evaluate(policy, session(outcomes=outcomes))

    assert check.status is LivenessStatus.NOT_PASSED
    assert check.issues == [LivenessIssue.TASK_NOT_COMPLETED]


@pytest.mark.parametrize(
    ("changes", "issue"),
    [
        ({"is_camera_available": False, "outcomes": []}, LivenessIssue.CAMERA_UNAVAILABLE),
        ({"is_model_available": False, "outcomes": []}, LivenessIssue.MODEL_UNAVAILABLE),
        ({"is_applicant_aligned": False, "outcomes": []}, LivenessIssue.APPLICANT_NOT_IN_FRAME),
        ({"max_people_in_frame": 2}, LivenessIssue.SEVERAL_PEOPLE_IN_FRAME),
    ],
)
def test_session_the_camera_could_not_follow_is_inconclusive(policy, changes, issue) -> None:
    check = evaluate(policy, session(**changes))

    assert check.status is LivenessStatus.INCONCLUSIVE
    assert issue in check.issues


def test_tasks_other_than_the_drawn_ones_do_not_pass(policy) -> None:
    easier = [outcome(LivenessTask.BLINK) for _ in DRAWN]

    check = evaluate(policy, session(outcomes=easier))

    assert check.status is LivenessStatus.NOT_PASSED
    assert LivenessIssue.TASKS_DIFFER_FROM_DRAWN in check.issues


def test_completed_task_is_recorded_by_the_sha256_of_its_frame(policy) -> None:
    check = evaluate(policy, session())

    frame = decode_frame(jpeg_data_url(), MAX_FRAME_BYTES)
    assert check.tasks[0].frame_sha256 == hashlib.sha256(frame).hexdigest()


def test_missed_task_keeps_no_frame(policy) -> None:
    outcomes = [outcome(DRAWN[0], is_completed=False), outcome(DRAWN[1]), outcome(DRAWN[2])]

    check = evaluate(policy, session(outcomes=outcomes))

    assert check.tasks[0].frame_sha256 is None


@pytest.mark.parametrize(
    "frame",
    [
        "https://example.com/frame.jpg",
        "data:image/jpeg;base64,not-base64!",
        "data:image/jpeg;base64," + base64.b64encode(b"GIF89a").decode(),
        "data:image/jpeg;base64," + base64.b64encode(b"\xff\xd8\xff" * 70_000).decode(),
    ],
    ids=["not a data URL", "bad base64", "not a JPEG", "too large"],
)
def test_unacceptable_frame_is_rejected(frame: str) -> None:
    with pytest.raises(LivenessFrameError):
        decode_frame(frame, MAX_FRAME_BYTES)


def test_audit_record_holds_frame_hashes_not_images(policy, stores) -> None:
    check = evaluate(policy, session())

    record_liveness_check(stores.audit_log, check, APPLICATION_ID, CUSTOMER_ID)

    record = stores.audit_log.find_latest(AuditEvent.LIVENESS_CHECKED, "customer_id", CUSTOMER_ID)
    assert record["frame_sha256"] == [task.frame_sha256 for task in check.tasks]
    assert "base64" not in str(record)


def test_attempts_count_only_this_customer(policy, stores) -> None:
    check = evaluate(policy, session())
    record_liveness_check(stores.audit_log, check, APPLICATION_ID, CUSTOMER_ID)
    record_liveness_check(stores.audit_log, check, "LA-TEST-0002", "CUS-002")

    assert attempts_in_last_day(stores.audit_log, CUSTOMER_ID, datetime.now(UTC)) == 1


def test_attempts_older_than_a_day_do_not_count(policy, stores) -> None:
    check = evaluate(policy, session())
    record_liveness_check(stores.audit_log, check, APPLICATION_ID, CUSTOMER_ID)

    a_day_later = datetime.now(UTC) + timedelta(hours=25)

    assert attempts_in_last_day(stores.audit_log, CUSTOMER_ID, a_day_later) == 0
