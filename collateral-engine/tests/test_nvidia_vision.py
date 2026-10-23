import json

import httpx
import pytest

from collateral_engine.domain import Condition
from collateral_engine.nvidia_vision import (
    DEFAULT_NVIDIA_VISION_MODEL,
    NvidiaConditionClassifier,
    extract_json_object,
)
from collateral_engine.vision import VisionFailure

CHAT_URL = "https://nvidia.example/v1/chat/completions"
TEST_API_KEY = "nvapi-test-key"
VALID_ANSWER = {
    "shows_apartment_interior": True,
    "contains_people": False,
    "condition": "green_frame",
    "confidence": "medium",
    "visible_evidence": ["puttied walls", "pipes in place"],
}


def completion(content: str | None, finish_reason: str = "stop") -> dict:
    return {"choices": [{"message": {"content": content}, "finish_reason": finish_reason}]}


def classify_with(answer: httpx.MockTransport):
    classifier = NvidiaConditionClassifier(
        httpx.Client(transport=answer), TEST_API_KEY, url=CHAT_URL, timeout_s=1.0
    )
    return classifier.classify(b"jpeg-bytes", "image/jpeg")


def answering(body: dict, status: int = 200) -> httpx.MockTransport:
    return httpx.MockTransport(lambda _: httpx.Response(status, json=body))


def test_valid_json_answer_becomes_assessment() -> None:
    classification = classify_with(answering(completion(json.dumps(VALID_ANSWER))))

    assert classification.failure is None
    assert classification.assessment.observed_condition is Condition.GREEN_FRAME


def test_request_sends_key_model_image_and_no_thinking() -> None:
    seen = {}

    def capture(request: httpx.Request) -> httpx.Response:
        seen["authorization"] = request.headers["Authorization"]
        seen["payload"] = json.loads(request.content)
        return httpx.Response(200, json=completion(json.dumps(VALID_ANSWER)))

    classify_with(httpx.MockTransport(capture))
    payload = seen["payload"]

    assert seen["authorization"] == f"Bearer {TEST_API_KEY}"
    assert payload["model"] == DEFAULT_NVIDIA_VISION_MODEL
    assert payload["chat_template_kwargs"] == {"enable_thinking": False}
    assert payload["messages"][1]["content"][1]["image_url"]["url"] == (
        "data:image/jpeg;base64,anBlZy1ieXRlcw=="
    )


@pytest.mark.parametrize(
    "content",
    [
        f"<think>walls look puttied</think>{json.dumps(VALID_ANSWER)}",
        f"```json\n{json.dumps(VALID_ANSWER)}\n```",
        f"Here is the result: {json.dumps(VALID_ANSWER)}",
    ],
)
def test_json_is_found_around_reasoning_and_fences(content: str) -> None:
    classification = classify_with(answering(completion(content)))

    assert classification.assessment.observed_condition is Condition.GREEN_FRAME


@pytest.mark.parametrize(
    "content",
    [
        "The flat looks renovated.",
        json.dumps({**VALID_ANSWER, "condition": "luxury"}),
        json.dumps({**VALID_ANSWER, "honesty_score": 0.9}),
        None,
    ],
)
def test_off_schema_answer_is_discarded(content: str | None) -> None:
    classification = classify_with(answering(completion(content)))

    assert (classification.assessment, classification.failure) == (
        None,
        VisionFailure.INVALID_OUTPUT,
    )


def test_cut_off_answer_is_truncated() -> None:
    classification = classify_with(answering(completion("{", finish_reason="length")))

    assert classification.failure is VisionFailure.TRUNCATED


def test_unexpected_body_is_invalid() -> None:
    assert classify_with(answering({"error": "nope"})).failure is VisionFailure.INVALID_OUTPUT


@pytest.mark.parametrize("status", [401, 429, 500, 503])
def test_http_error_makes_photo_unassessed(status: int) -> None:
    classification = classify_with(answering({"detail": "error"}, status=status))

    assert classification.failure is VisionFailure.UNAVAILABLE


def test_timeout_makes_photo_unassessed() -> None:
    def time_out(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow", request=request)

    assert classify_with(httpx.MockTransport(time_out)).failure is VisionFailure.UNAVAILABLE


def test_api_key_is_not_logged(caplog: pytest.LogCaptureFixture) -> None:
    classify_with(answering({"detail": "unauthorised"}, status=401))

    assert TEST_API_KEY not in caplog.text


def test_extract_returns_none_without_object() -> None:
    assert extract_json_object("<think>{draft}</think> no answer") is None
