"""Condition classifier on NVIDIA hosted models (build.nvidia.com), OpenAI-compatible chat API.

The hosted endpoint has no strict JSON-schema mode, so the schema is spelled out in the prompt and
the answer is validated exactly as for Claude: anything off-schema is discarded and the photo
counts as not assessed. The API key is sent in a header only and never logged.
"""

import base64
import logging
import re

import httpx
from pydantic import BaseModel, ConfigDict, ValidationError

from collateral_engine.domain import Condition
from collateral_engine.vision import (
    SYSTEM_PROMPT,
    UNDETERMINED,
    USER_INSTRUCTION,
    PhotoClassification,
    VisionConfidence,
    VisionFailure,
    classification_from_json,
)

logger = logging.getLogger(__name__)

DEFAULT_NVIDIA_CHAT_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
DEFAULT_NVIDIA_VISION_MODEL = "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning"
NVIDIA_MAX_TOKENS = 2048
# Zero temperature: the same photo should get the same class on every run.
NVIDIA_TEMPERATURE = 0.0
TRUNCATED_FINISH_REASON = "length"
_THINKING_BLOCK = re.compile(r"<think>.*?</think>", re.DOTALL)

JSON_ANSWER_INSTRUCTION = (
    "Answer with one JSON object and nothing else, with exactly these keys: "
    '"shows_apartment_interior" (true or false), "contains_people" (true or false), '
    f'"condition" (one of: {", ".join([*Condition, UNDETERMINED])}), '
    f'"confidence" (one of: {", ".join(VisionConfidence)}), '
    '"visible_evidence" (a list of up to five short strings).'
)


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


class NvidiaConditionClassifier:
    def __init__(
        self,
        http_client: httpx.Client,
        api_key: str,
        model: str = DEFAULT_NVIDIA_VISION_MODEL,
        url: str = DEFAULT_NVIDIA_CHAT_URL,
        timeout_s: float = 60.0,
    ) -> None:
        self._http_client = http_client
        self._api_key = api_key
        self._model = model
        self._url = url
        self._timeout_s = timeout_s

    def classify(self, image: bytes, media_type: str) -> PhotoClassification:
        try:
            response = self._http_client.post(
                self._url,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Accept": "application/json",
                },
                json=self._payload(image, media_type),
                timeout=self._timeout_s,
            )
            response.raise_for_status()
            body = response.json()
        except httpx.TimeoutException:
            logger.warning("NVIDIA vision request timed out after %s s", self._timeout_s)
            return PhotoClassification(None, VisionFailure.UNAVAILABLE)
        except httpx.HTTPStatusError as error:
            logger.error("NVIDIA vision request rejected: status %s", error.response.status_code)
            return PhotoClassification(None, VisionFailure.UNAVAILABLE)
        except httpx.HTTPError as error:
            logger.warning("NVIDIA vision service unreachable: %s", type(error).__name__)
            return PhotoClassification(None, VisionFailure.UNAVAILABLE)
        except ValueError:
            return PhotoClassification(None, VisionFailure.INVALID_OUTPUT)
        return parse_chat_completion(body)

    def _payload(self, image: bytes, media_type: str) -> dict[str, object]:
        data_url = f"data:{media_type};base64,{base64.standard_b64encode(image).decode('ascii')}"
        return {
            "model": self._model,
            "messages": [
                {"role": "system", "content": f"{SYSTEM_PROMPT}\n\n{JSON_ANSWER_INSTRUCTION}"},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": USER_INSTRUCTION},
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


def parse_chat_completion(body: object) -> PhotoClassification:
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
    return classification_from_json(answer)


def extract_json_object(content: str) -> str | None:
    """The outermost {...} after any reasoning block; it is then validated strictly."""
    visible = _THINKING_BLOCK.sub("", content)
    start, end = visible.find("{"), visible.rfind("}")
    if start == -1 or end < start:
        return None
    return visible[start : end + 1]
