"""Step 2 of the loan application: remote identification by liveness tasks (NBG Order 104/04).

The camera, the face landmark model and the tasks run in the browser component in
components/liveness. The tasks are drawn here and the bank's rules in lending/liveness.py set the
status, so the browser can neither choose easier tasks nor give its own verdict.
"""

import random
import uuid
from datetime import UTC, datetime
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components
from pydantic import ValidationError

import design
from collateral_engine.i18n import Language
from collateral_engine.lending.customer import CustomerFile
from collateral_engine.lending.liveness import (
    LivenessCheck,
    LivenessFrameError,
    LivenessSession,
    LivenessStatus,
    LivenessTask,
    LivenessTaskResult,
    attempts_in_last_day,
    draw_tasks,
    evaluate_session,
    record_liveness_check,
)
from collateral_engine.lending.policy import LivenessPolicy, load_lending_policy
from collateral_engine.lending.texts import (
    LIVENESS_ISSUE_NAMES,
    LIVENESS_STATUS_NAMES,
    LIVENESS_TASK_NAMES,
)
from report_view import label
from resources import get_stores

COMPONENT_DIRECTORY = Path(__file__).parent / "components" / "liveness"
MEDIAPIPE_VERSION = "0.10.14"
MEDIAPIPE_PACKAGE_URL = f"https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@{MEDIAPIPE_VERSION}"
FACE_LANDMARKER_MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/"
    "face_landmarker.task"
)
MEDIAPIPE_URLS = {
    "bundle": f"{MEDIAPIPE_PACKAGE_URL}/vision_bundle.mjs",
    "wasm": f"{MEDIAPIPE_PACKAGE_URL}/wasm",
    "model": FACE_LANDMARKER_MODEL_URL,
}
# Settings the browser needs to follow the tasks; the status itself is set in Python.
BROWSER_POLICY_FIELDS = {
    "task_timeout_ms",
    "align_timeout_ms",
    "min_head_turn",
    "min_head_tilt",
    "eye_closed_score",
    "eye_open_score",
    "hold_frames",
    "frame_width_px",
}
COMPONENT_TEXT_KEYS = (
    "kicker",
    "start_title",
    "idle",
    "start_button",
    "loading",
    "align_title",
    "align_hint",
    "task_hint",
    "several_people",
    "no_face",
    "task_done",
    "done_title",
    "done_hint",
    "privacy",
    "model_label",
    "frames_label",
    "people_label",
)
STATUS_COLOURS = {
    LivenessStatus.PASSED: "#1f9d55",
    LivenessStatus.NOT_PASSED: "#b7791f",
    LivenessStatus.INCONCLUSIVE: "#8a94a6",
}
STATE_PREFIX = "loan_"
# The frames live only in this session's memory, for the officer to see; they are never written.
LIVENESS_STATE_NAMES = ("liveness", "liveness_frames", "liveness_session", "liveness_tasks")
MILLISECONDS_PER_SECOND = 1000

_liveness_component = components.declare_component("liveness_check", path=str(COMPONENT_DIRECTORY))


def _state(name: str) -> object:
    return st.session_state.get(f"{STATE_PREFIX}{name}")


def _set_state(name: str, value: object) -> None:
    st.session_state[f"{STATE_PREFIX}{name}"] = value


def clear_liveness() -> None:
    for name in (*LIVENESS_STATE_NAMES, "report"):
        st.session_state.pop(f"{STATE_PREFIX}{name}", None)


def current_check() -> LivenessCheck | None:
    check = _state("liveness")
    return check if isinstance(check, LivenessCheck) else None


def render_identification(
    customer_file: CustomerFile | None, application_id: str | None, language: Language
) -> None:
    with st.container(border=True):
        st.markdown(
            f'<div class="setup-step">{label("step_identification", language)}</div>',
            unsafe_allow_html=True,
        )
        policy = load_lending_policy().liveness
        design.ai_header(
            label("liveness_title", language),
            "",
            label("liveness_note", language, count=policy.task_count),
        )
        if customer_file is None or application_id is None:
            st.caption(label("liveness_need_data", language))
            return
        if customer_file.customer.age < policy.min_applicant_age:
            st.info(label("liveness_too_young", language, age=policy.min_applicant_age))
            return
        check = current_check()
        if check is not None:
            render_check(check, language)
            if check.status is not LivenessStatus.PASSED:
                _render_retry(customer_file, policy, language)
            return
        _render_session(customer_file, application_id, policy, language)


def _attempts_used(customer_file: CustomerFile) -> int:
    return attempts_in_last_day(
        get_stores().audit_log, customer_file.customer.customer_id, datetime.now(UTC)
    )


def _render_retry(customer_file: CustomerFile, policy: LivenessPolicy, language: Language) -> None:
    if _attempts_used(customer_file) >= policy.max_attempts_per_day:
        st.warning(label("liveness_attempts_used", language, max=policy.max_attempts_per_day))
        return
    st.button(label("liveness_retry", language), on_click=clear_liveness, key="loan_liveness_retry")


def _render_session(
    customer_file: CustomerFile, application_id: str, policy: LivenessPolicy, language: Language
) -> None:
    attempts_used = _attempts_used(customer_file)
    if attempts_used >= policy.max_attempts_per_day:
        st.warning(label("liveness_attempts_used", language, max=policy.max_attempts_per_day))
        return
    if _state("liveness_session") is None:
        # The operating system's randomness: the tasks must not be predictable (NBG 104/04).
        _set_state("liveness_tasks", draw_tasks(policy, random.SystemRandom()))
        _set_state("liveness_session", uuid.uuid4().hex)
    tasks: tuple[LivenessTask, ...] = _state("liveness_tasks")
    session_id: str = _state("liveness_session")
    attempt = attempts_used + 1
    st.caption(
        label("liveness_attempt", language, attempt=attempt, max=policy.max_attempts_per_day)
        + " · "
        + label("liveness_skip_hint", language)
    )
    value = _liveness_component(
        session_id=session_id,
        tasks=[{"id": task.value, "title": LIVENESS_TASK_NAMES[task][language]} for task in tasks],
        texts=_component_texts(policy, language),
        policy=policy.model_dump(include=BROWSER_POLICY_FIELDS),
        urls=MEDIAPIPE_URLS,
        key=f"loan_liveness_component_{session_id}",
        default=None,
    )
    if value is not None:
        _accept_session(value, customer_file, application_id, attempt, language)


def _component_texts(policy: LivenessPolicy, language: Language) -> dict[str, str]:
    texts = {key: label(f"lv_{key}", language) for key in COMPONENT_TEXT_KEYS}
    texts["start_hint"] = label("lv_start_hint", language, count=policy.task_count)
    texts["task_missed"] = label("liveness_missed", language)
    # The browser fills in the task number itself.
    texts["step"] = label("lv_step", language, n="{n}", total="{total}")
    return texts


def _accept_session(
    value: object,
    customer_file: CustomerFile,
    application_id: str,
    attempt: int,
    language: Language,
) -> None:
    try:
        session = LivenessSession.model_validate(value)
    except ValidationError as error:
        st.error(label("liveness_invalid", language, error=error.errors()[0]["msg"]))
        return
    if session.session_id != _state("liveness_session"):
        return
    lending_policy = load_lending_policy()
    stores = get_stores()
    try:
        check = evaluate_session(
            session,
            _state("liveness_tasks"),
            attempt,
            lending_policy.liveness,
            lending_policy.version,
        )
    except LivenessFrameError as error:
        st.error(label("liveness_invalid", language, error=str(error)))
        return
    record_liveness_check(
        stores.audit_log, check, application_id, customer_file.customer.customer_id
    )
    clear_liveness()
    _set_state("liveness", check)
    _set_state(
        "liveness_frames",
        {
            task.frame_sha256: outcome.frame_jpeg
            for task, outcome in zip(check.tasks, session.outcomes, strict=True)
            if task.frame_sha256 is not None
        },
    )
    st.rerun()


def render_check(check: LivenessCheck, language: Language) -> None:
    completed = sum(task.is_completed for task in check.tasks)
    design.liveness_card(
        design.LivenessCard(
            title=label("liveness_title", language),
            status=LIVENESS_STATUS_NAMES[check.status][language],
            colour=STATUS_COLOURS[check.status],
            summary=label(
                "liveness_tasks_done",
                language,
                completed=completed,
                total=len(check.tasks),
                frames=check.frames_analysed,
            ),
            frames=[_frame(task, language) for task in check.tasks],
            issues=[LIVENESS_ISSUE_NAMES[issue][language] for issue in check.issues],
            note=label("liveness_not_stored", language),
        )
    )


def _frame(task: LivenessTaskResult, language: Language) -> design.LivenessFrame:
    state = (
        f"✓ {label('lv_task_done', language)} · {task.response_ms / MILLISECONDS_PER_SECOND:.1f} s"
        if task.is_completed
        else f"✕ {label('liveness_missed', language)}"
    )
    return design.LivenessFrame(
        title=LIVENESS_TASK_NAMES[task.task][language],
        state=state,
        is_completed=task.is_completed,
        image_data_url=_frame_data_url(task.frame_sha256),
        sha256=task.frame_sha256,
    )


def _frame_data_url(sha256: str | None) -> str | None:
    frames = _state("liveness_frames") or {}
    return frames.get(sha256) if sha256 is not None else None
