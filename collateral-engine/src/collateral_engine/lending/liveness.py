"""Remote identification of the applicant by liveness tasks (NBG Order 104/04).

The applicant performs randomly chosen tasks in front of the camera: turn the head, look up or
down, blink. A face landmark model in the browser follows the movements and reports
what happened; this module draws the tasks, sets the status by the bank's rules and writes the
session to the audit log. The frames are not stored: the log keeps only their SHA-256.

It infers nothing about the person: no face template, no face matching, no age, gender or
emotion. A session the camera or the model could not follow is INCONCLUSIVE, never a failure,
and nothing is refused automatically: the officer identifies the applicant in a branch instead.
"""

import base64
import binascii
import hashlib
import random
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from collateral_engine.audit import AuditEvent, AuditLog
from collateral_engine.lending.policy import LivenessPolicy

LIVENESS_MODEL = "MediaPipe Face Landmarker"
ATTEMPT_WINDOW = timedelta(hours=24)
JPEG_DATA_URL_PREFIX = "data:image/jpeg;base64,"
JPEG_MAGIC = b"\xff\xd8\xff"
MAX_PEOPLE_IN_FRAME = 1


class LivenessTask(StrEnum):
    TURN_LEFT = "turn_left"
    TURN_RIGHT = "turn_right"
    LOOK_UP = "look_up"
    LOOK_DOWN = "look_down"
    BLINK = "blink"


class LivenessStatus(StrEnum):
    PASSED = "passed"
    NOT_PASSED = "not_passed"
    INCONCLUSIVE = "inconclusive"


class LivenessIssue(StrEnum):
    CAMERA_UNAVAILABLE = "camera_unavailable"
    MODEL_UNAVAILABLE = "model_unavailable"
    APPLICANT_NOT_IN_FRAME = "applicant_not_in_frame"
    SEVERAL_PEOPLE_IN_FRAME = "several_people_in_frame"
    TASKS_DIFFER_FROM_DRAWN = "tasks_differ_from_drawn"
    TASK_NOT_COMPLETED = "task_not_completed"


# Issues that say the session could not be followed, not that the applicant failed a task.
INCONCLUSIVE_ISSUES = frozenset(
    {
        LivenessIssue.CAMERA_UNAVAILABLE,
        LivenessIssue.MODEL_UNAVAILABLE,
        LivenessIssue.APPLICANT_NOT_IN_FRAME,
        LivenessIssue.SEVERAL_PEOPLE_IN_FRAME,
    }
)


class LivenessFrameError(ValueError):
    """An evidence frame from the browser is not a JPEG within the size limit."""


class _Model(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class TaskOutcome(_Model):
    """One task as the browser saw it."""

    task: LivenessTask
    is_completed: bool
    response_ms: Annotated[int, Field(ge=0)]
    frame_jpeg: str | None = None


class LivenessSession(_Model):
    """What the browser reports at the end of a session; untrusted input."""

    session_id: Annotated[str, Field(min_length=1, max_length=64)]
    is_camera_available: bool
    is_model_available: bool
    is_applicant_aligned: bool
    frames_analysed: Annotated[int, Field(ge=0)]
    max_people_in_frame: Annotated[int, Field(ge=0)]
    outcomes: list[TaskOutcome]


class LivenessTaskResult(_Model):
    task: LivenessTask
    is_completed: bool
    response_ms: int
    frame_sha256: str | None


class LivenessCheck(_Model):
    session_id: str
    attempt: int
    status: LivenessStatus
    issues: list[LivenessIssue]
    tasks: list[LivenessTaskResult]
    frames_analysed: int
    model: str
    policy_version: str


def draw_tasks(policy: LivenessPolicy, chooser: random.Random) -> tuple[LivenessTask, ...]:
    """Distinct tasks in random order; the browser cannot choose easier ones."""
    return tuple(chooser.sample(list(LivenessTask), policy.task_count))


def session_issues(
    session: LivenessSession, drawn: tuple[LivenessTask, ...]
) -> list[LivenessIssue]:
    if not session.is_camera_available:
        return [LivenessIssue.CAMERA_UNAVAILABLE]
    if not session.is_model_available:
        return [LivenessIssue.MODEL_UNAVAILABLE]
    if not session.is_applicant_aligned:
        return [LivenessIssue.APPLICANT_NOT_IN_FRAME]
    issues: list[LivenessIssue] = []
    if session.max_people_in_frame > MAX_PEOPLE_IN_FRAME:
        issues.append(LivenessIssue.SEVERAL_PEOPLE_IN_FRAME)
    if tuple(outcome.task for outcome in session.outcomes) != drawn:
        issues.append(LivenessIssue.TASKS_DIFFER_FROM_DRAWN)
    if not all(outcome.is_completed for outcome in session.outcomes):
        issues.append(LivenessIssue.TASK_NOT_COMPLETED)
    return issues


def liveness_status(issues: list[LivenessIssue]) -> LivenessStatus:
    if any(issue in INCONCLUSIVE_ISSUES for issue in issues):
        return LivenessStatus.INCONCLUSIVE
    if issues:
        return LivenessStatus.NOT_PASSED
    return LivenessStatus.PASSED


def decode_frame(frame_jpeg: str, max_bytes: int) -> bytes:
    if not frame_jpeg.startswith(JPEG_DATA_URL_PREFIX):
        raise LivenessFrameError("an evidence frame must be a JPEG data URL")
    try:
        content = base64.b64decode(frame_jpeg.removeprefix(JPEG_DATA_URL_PREFIX), validate=True)
    except binascii.Error as error:
        raise LivenessFrameError(f"an evidence frame is not valid base64: {error}") from error
    if not content.startswith(JPEG_MAGIC):
        raise LivenessFrameError("an evidence frame is not a JPEG image")
    if len(content) > max_bytes:
        raise LivenessFrameError(f"an evidence frame is larger than {max_bytes} bytes")
    return content


def frame_content(outcome: TaskOutcome, max_bytes: int) -> bytes | None:
    """The frame of a completed task; a missed task has none."""
    if not outcome.is_completed or outcome.frame_jpeg is None:
        return None
    return decode_frame(outcome.frame_jpeg, max_bytes)


def frame_sha256(outcome: TaskOutcome, max_bytes: int) -> str | None:
    content = frame_content(outcome, max_bytes)
    return hashlib.sha256(content).hexdigest() if content is not None else None


def evaluate_session(
    session: LivenessSession,
    drawn: tuple[LivenessTask, ...],
    attempt: int,
    policy: LivenessPolicy,
    policy_version: str,
) -> LivenessCheck:
    """Raises LivenessFrameError when an evidence frame is not acceptable."""
    issues = session_issues(session, drawn)
    tasks = [
        LivenessTaskResult(
            task=outcome.task,
            is_completed=outcome.is_completed,
            response_ms=outcome.response_ms,
            frame_sha256=frame_sha256(outcome, policy.max_frame_bytes),
        )
        for outcome in session.outcomes
    ]
    return LivenessCheck(
        session_id=session.session_id,
        attempt=attempt,
        status=liveness_status(issues),
        issues=issues,
        tasks=tasks,
        frames_analysed=session.frames_analysed,
        model=LIVENESS_MODEL,
        policy_version=policy_version,
    )


def record_liveness_check(
    audit_log: AuditLog, check: LivenessCheck, application_id: str, customer_id: str
) -> str:
    """Only the hashes of the frames go to the log, never the images."""
    return audit_log.append(
        {
            "event": AuditEvent.LIVENESS_CHECKED,
            "application_id": application_id,
            "customer_id": customer_id,
            "session_id": check.session_id,
            "attempt": check.attempt,
            "status": check.status,
            "issues": list(check.issues),
            "tasks": [task.task for task in check.tasks],
            "frame_sha256": [task.frame_sha256 for task in check.tasks if task.frame_sha256],
            "policy_version": check.policy_version,
        }
    )


def attempts_in_last_day(audit_log: AuditLog, customer_id: str, now: datetime) -> int:
    """Sessions of this customer in the 24 hours before now; now must carry a time zone."""
    since = now - ATTEMPT_WINDOW
    return sum(
        datetime.fromisoformat(record.recorded_at) > since
        for record in audit_log.records_of(AuditEvent.LIVENESS_CHECKED, "customer_id", customer_id)
    )
