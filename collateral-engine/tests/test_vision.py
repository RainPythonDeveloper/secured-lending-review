import json

import anthropic
import httpx2
import pytest

from builders import FakeAnthropicMessages, fake_anthropic_client, fake_message
from collateral_engine.domain import Condition
from collateral_engine.vision import (
    ASSESSMENT_JSON_SCHEMA,
    DEFAULT_VISION_MODEL,
    SERVER_SIDE_FALLBACK_BETA,
    ClaudeConditionClassifier,
    VisionConfidence,
    VisionFailure,
)

VALID_ANSWER = {
    "shows_apartment_interior": True,
    "contains_people": False,
    "condition": "white_frame",
    "confidence": "high",
    "visible_evidence": ["plastered walls", "screeded concrete floor"],
}
API_REQUEST = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")


def classify_with(messages: FakeAnthropicMessages):
    classifier = ClaudeConditionClassifier(fake_anthropic_client(messages))
    return classifier.classify(b"jpeg-bytes", "image/jpeg")


def test_valid_answer_becomes_assessment() -> None:
    messages = FakeAnthropicMessages(response=fake_message(json.dumps(VALID_ANSWER)))

    classification = classify_with(messages)

    assert classification.failure is None
    assert classification.assessment.observed_condition is Condition.WHITE_FRAME
    assert classification.assessment.confidence is VisionConfidence.HIGH


def test_request_sends_image_schema_and_fallback() -> None:
    messages = FakeAnthropicMessages(response=fake_message(json.dumps(VALID_ANSWER)))

    classify_with(messages)
    request = messages.requests[0]

    assert request["model"] == DEFAULT_VISION_MODEL
    assert request["betas"] == [SERVER_SIDE_FALLBACK_BETA]
    assert request["fallbacks"] == "default"
    assert request["output_config"]["format"]["schema"] == ASSESSMENT_JSON_SCHEMA
    image_block = request["messages"][0]["content"][0]
    assert image_block["source"] == {
        "type": "base64",
        "media_type": "image/jpeg",
        "data": "anBlZy1ieXRlcw==",
    }


def test_undetermined_condition_has_no_observed_condition() -> None:
    answer = {**VALID_ANSWER, "condition": "undetermined", "confidence": "low"}

    classification = classify_with(FakeAnthropicMessages(response=fake_message(json.dumps(answer))))

    assert classification.assessment.observed_condition is None


@pytest.mark.parametrize(
    "answer_text",
    [
        "this is not json",
        json.dumps({**VALID_ANSWER, "condition": "luxury"}),
        json.dumps({**VALID_ANSWER, "honesty_score": 0.2}),
        json.dumps({key: value for key, value in VALID_ANSWER.items() if key != "confidence"}),
        json.dumps({**VALID_ANSWER, "visible_evidence": ["x" * 500]}),
    ],
)
def test_off_schema_answer_is_discarded(answer_text: str) -> None:
    classification = classify_with(FakeAnthropicMessages(response=fake_message(answer_text)))

    assert (classification.assessment, classification.failure) == (
        None,
        VisionFailure.INVALID_OUTPUT,
    )


@pytest.mark.parametrize(
    ("stop_reason", "failure"),
    [("refusal", VisionFailure.REFUSED), ("max_tokens", VisionFailure.TRUNCATED)],
)
def test_incomplete_answer_is_a_failure(stop_reason: str, failure: VisionFailure) -> None:
    response = fake_message(json.dumps(VALID_ANSWER), stop_reason=stop_reason)

    assert classify_with(FakeAnthropicMessages(response=response)).failure is failure


def test_answer_without_text_is_invalid() -> None:
    response = fake_message(None)

    assert classify_with(FakeAnthropicMessages(response=response)).failure is (
        VisionFailure.INVALID_OUTPUT
    )


@pytest.mark.parametrize(
    "error",
    [
        anthropic.APIConnectionError(request=API_REQUEST),
        anthropic.APITimeoutError(request=API_REQUEST),
        anthropic.InternalServerError(
            "overloaded", response=httpx2.Response(529, request=API_REQUEST), body=None
        ),
        anthropic.AuthenticationError(
            "bad key", response=httpx2.Response(401, request=API_REQUEST), body=None
        ),
    ],
)
def test_api_error_makes_photo_unassessed(error: Exception) -> None:
    classification = classify_with(FakeAnthropicMessages(error=error))

    assert (classification.assessment, classification.failure) == (
        None,
        VisionFailure.UNAVAILABLE,
    )
