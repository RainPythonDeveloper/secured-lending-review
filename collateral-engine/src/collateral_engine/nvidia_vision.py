"""Photo classifier on NVIDIA hosted models (build.nvidia.com), OpenAI-compatible chat API.

The hosted endpoint has no strict JSON-schema mode, so the schema is spelled out in the prompt and
the answer is validated exactly as for Claude: anything off-schema is discarded and the photo
counts as not assessed. The API key is sent in a header only and never logged.
"""

import base64
import logging
import random
import re
import time
from collections.abc import Callable

import httpx
from pydantic import BaseModel, ConfigDict, ValidationError

from collateral_engine.vision import (
    CONDITION_TASK,
    PhotoClassification,
    VisionFailure,
    VisionTask,
    classification_from_json,
)

logger = logging.getLogger(__name__)

DEFAULT_NVIDIA_CHAT_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
DEFAULT_NVIDIA_VISION_MODEL = "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning"
NVIDIA_MAX_TOKENS = 2048
# Zero temperature: the same photo should get the same class on every run.
NVIDIA_TEMPERATURE = 0.0
TRUNCATED_FINISH_REASON = "length"
# The free hosted endpoint answers 503 "ResourceExhausted" when its shared workers are saturated;
# such refusals pass within seconds, so they are retried. A timeout is not: it already took
# timeout_s. Rejections such as 401 never succeed on retry.
RETRYABLE_STATUS_CODES = frozenset({429, 500, 502, 503, 504})
MAX_ATTEMPTS = 3
RETRY_BASE_DELAY_S = 2.0
# Share of the delay added at random, so that parallel requests do not retry in step.
RETRY_JITTER_SHARE = 0.5
_THINKING_BLOCK = re.compile(r"<think>.*?</think>", re.DOTALL)


class _ChatMessage(BaseModel):
    model_config = ConfigDict(extra="ignore")

    content: str | None = None


class _ChatChoice(BaseModel):
    model_config = ConfigDict(extra="ignore")

    message: _ChatMessage
    finish_reason: str | None = None


class _ChatCompletion(BaseModel):
    model_config = ConfigDict(extra="ignore")

    choices: list[_ChatChoice]


class _RetryableStatusError(Exception):
    def __init__(self, status_code: int) -> None:
        super().__init__(f"status {status_code}")
        self.status_code = status_code


class NvidiaVisionClassifier:
    def __init__(
        self,
        http_client: httpx.Client,
        api_key: str,
        model: str = DEFAULT_NVIDIA_VISION_MODEL,
        url: str = DEFAULT_NVIDIA_CHAT_URL,
        timeout_s: float = 60.0,
        sleep: Callable[[float], None] = time.sleep,
        jitter: Callable[[], float] = random.random,
        task: VisionTask = CONDITION_TASK,
    ) -> None:
        self._task = task
        self._http_client = http_client
        self._api_key = api_key
        self._model = model
        self._url = url
        self._timeout_s = timeout_s
        self._sleep = sleep
        self._jitter = jitter

    @property
    def model_name(self) -> str:
        return self._model

    def classify(self, image: bytes, media_type: str) -> PhotoClassification:
        payload = self._payload(image, media_type)
        for attempt in range(1, MAX_ATTEMPTS):
            try:
                return self._classify_once(payload)
            except _RetryableStatusError as error:
                self._wait_before_retry(attempt, error.status_code)
        try:
            return self._classify_once(payload)
        except _RetryableStatusError as error:
            logger.error(
                "NVIDIA vision unavailable: status %s after %s attempts",
                error.status_code,
                MAX_ATTEMPTS,
            )
            return PhotoClassification(None, VisionFailure.UNAVAILABLE)

    def _wait_before_retry(self, attempt: int, status_code: int) -> None:
        delay_s = (
            RETRY_BASE_DELAY_S * 2 ** (attempt - 1) * (1 + RETRY_JITTER_SHARE * self._jitter())
        )
        logger.warning(
            "NVIDIA vision busy (status %s), attempt %s of %s; retrying in %.1f s",
            status_code,
            attempt,
            MAX_ATTEMPTS,
            delay_s,
        )
        self._sleep(delay_s)

    def _classify_once(self, payload: dict[str, object]) -> PhotoClassification:
        """Raises _RetryableStatusError when the endpoint is busy."""
        try:
            response = self._http_client.post(
                self._url,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Accept": "application/json",
                },
                json=payload,
                timeout=self._timeout_s,
            )
            response.raise_for_status()
            body = response.json()
        except httpx.TimeoutException:
            logger.warning("NVIDIA vision request timed out after %s s", self._timeout_s)
            return PhotoClassification(None, VisionFailure.UNAVAILABLE)
        except httpx.HTTPStatusError as error:
            status_code = error.response.status_code
            if status_code in RETRYABLE_STATUS_CODES:
                raise _RetryableStatusError(status_code) from error
            logger.error("NVIDIA vision request rejected: status %s", status_code)
            return PhotoClassification(None, VisionFailure.UNAVAILABLE)
        except httpx.HTTPError as error:
            logger.warning("NVIDIA vision service unreachable: %s", type(error).__name__)
            return PhotoClassification(None, VisionFailure.UNAVAILABLE)
        except ValueError:
            return PhotoClassification(None, VisionFailure.INVALID_OUTPUT)
        return parse_chat_completion(body, self._task.answer_model)

    def _payload(self, image: bytes, media_type: str) -> dict[str, object]:
        data_url = f"data:{media_type};base64,{base64.standard_b64encode(image).decode('ascii')}"
        return {
            "model": self._model,
            "messages": [
                {
                    "role": "system",
                    "content": f"{self._task.system_prompt}\n\n{self._task.answer_instruction}",
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": self._task.user_instruction},
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ],
                },
            ],
            "max_tokens": NVIDIA_MAX_TOKENS,
            "temperature": NVIDIA_TEMPERATURE,
            "stream": False,
            # A short classification does not need visible chain of thought.
            "chat_template_kwargs": {"enable_thinking": False},
        }


def parse_chat_completion(body: object, answer_model: type[BaseModel]) -> PhotoClassification:
    try:
        completion = _ChatCompletion.model_validate(body)
    except ValidationError:
        return PhotoClassification(None, VisionFailure.INVALID_OUTPUT)
    if not completion.choices or completion.choices[0].message.content is None:
        return PhotoClassification(None, VisionFailure.INVALID_OUTPUT)
    choice = completion.choices[0]
    if choice.finish_reason == TRUNCATED_FINISH_REASON:
        return PhotoClassification(None, VisionFailure.TRUNCATED)
    answer = extract_json_object(choice.message.content)
    if answer is None:
        return PhotoClassification(None, VisionFailure.INVALID_OUTPUT)
    return classification_from_json(answer, answer_model)


def extract_json_object(content: str) -> str | None:
    """The outermost {...} after any reasoning block; it is then validated strictly."""
    visible = _THINKING_BLOCK.sub("", content)
    start, end = visible.find("{"), visible.rfind("}")
    if start == -1 or end < start:
        return None
    return visible[start : end + 1]
