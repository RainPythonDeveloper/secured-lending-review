"""Checks on uploaded photos that run before any model looks at them.

A photo that is unreadable, too small, too dark or blurred is not judged at all: it can only make
the condition check INCONCLUSIVE, never CONTRADICTED.
"""

import hashlib
import io
from dataclasses import dataclass
from enum import StrEnum

import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

from collateral_engine.policy import PhotoPolicy

SHARPNESS_WORKING_WIDTH_PX = 512
DIFFERENCE_HASH_SIZE = 8
VISION_MAX_EDGE_PX = 1568
VISION_JPEG_QUALITY = 85
MEDIA_TYPE_BY_FORMAT = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}


class PhotoQualityIssue(StrEnum):
    TOO_LARGE_FILE = "TOO_LARGE_FILE"
    UNREADABLE = "UNREADABLE"
    UNSUPPORTED_FORMAT = "UNSUPPORTED_FORMAT"
    LOW_RESOLUTION = "LOW_RESOLUTION"
    TOO_DARK = "TOO_DARK"
    TOO_BRIGHT = "TOO_BRIGHT"
    BLURRY = "BLURRY"


@dataclass(frozen=True)
class PhotoUpload:
    filename: str
    content: bytes


@dataclass(frozen=True)
class PhotoInspection:
    sha256: str
    width_px: int | None
    height_px: int | None
    mean_brightness: float | None
    sharpness: float | None
    difference_hash: int | None
    quality_issues: tuple[PhotoQualityIssue, ...]

    @property
    def is_usable(self) -> bool:
        return not self.quality_issues


def inspect_photo(content: bytes, policy: PhotoPolicy) -> PhotoInspection:
    sha256 = hashlib.sha256(content).hexdigest()
    if len(content) > policy.max_bytes:
        return _rejected(sha256, PhotoQualityIssue.TOO_LARGE_FILE)
    try:
        image = _decode(content)
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError, ValueError):
        return _rejected(sha256, PhotoQualityIssue.UNREADABLE)
    if image.format not in MEDIA_TYPE_BY_FORMAT:
        return _rejected(sha256, PhotoQualityIssue.UNSUPPORTED_FORMAT)
    grey = ImageOps.exif_transpose(image).convert("L")
    mean_brightness = float(np.asarray(grey, dtype=float).mean())
    sharpness = laplacian_variance(grey)
    return PhotoInspection(
        sha256=sha256,
        width_px=grey.width,
        height_px=grey.height,
        mean_brightness=mean_brightness,
        sharpness=sharpness,
        difference_hash=difference_hash(grey),
        quality_issues=_quality_issues(grey.size, mean_brightness, sharpness, policy),
    )


def _decode(content: bytes) -> Image.Image:
    image = Image.open(io.BytesIO(content))
    image.load()
    return image


def _rejected(sha256: str, issue: PhotoQualityIssue) -> PhotoInspection:
    return PhotoInspection(sha256, None, None, None, None, None, (issue,))


def _quality_issues(
    size_px: tuple[int, int], mean_brightness: float, sharpness: float, policy: PhotoPolicy
) -> tuple[PhotoQualityIssue, ...]:
    width_px, height_px = sorted(size_px, reverse=True)
    issues = []
    if width_px < policy.min_width_px or height_px < policy.min_height_px:
        issues.append(PhotoQualityIssue.LOW_RESOLUTION)
    if mean_brightness < policy.min_mean_brightness:
        issues.append(PhotoQualityIssue.TOO_DARK)
    if mean_brightness > policy.max_mean_brightness:
        issues.append(PhotoQualityIssue.TOO_BRIGHT)
    if sharpness < policy.min_sharpness:
        issues.append(PhotoQualityIssue.BLURRY)
    return tuple(issues)


def laplacian_variance(grey: Image.Image) -> float:
    """Focus measure; computed on a fixed-width copy so that it does not depend on resolution."""
    height_px = max(3, round(grey.height * SHARPNESS_WORKING_WIDTH_PX / grey.width))
    pixels = np.asarray(
        grey.resize((SHARPNESS_WORKING_WIDTH_PX, height_px), Image.Resampling.BOX), dtype=float
    )
    laplacian = (
        pixels[1:-1, :-2]
        + pixels[1:-1, 2:]
        + pixels[:-2, 1:-1]
        + pixels[2:, 1:-1]
        - 4 * pixels[1:-1, 1:-1]
    )
    return float(laplacian.var())


def difference_hash(grey: Image.Image) -> int:
    """64-bit perceptual hash: survives resizing and recompression, unlike SHA-256."""
    small = np.asarray(
        grey.resize((DIFFERENCE_HASH_SIZE + 1, DIFFERENCE_HASH_SIZE), Image.Resampling.BOX),
        dtype=float,
    )
    bits = (small[:, 1:] > small[:, :-1]).flatten()
    return int("".join("1" if bit else "0" for bit in bits), 2)


def hamming_distance(first_hash: int, second_hash: int) -> int:
    return (first_hash ^ second_hash).bit_count()


def near_duplicate_pairs(
    inspections: list[PhotoInspection], max_hamming: int
) -> list[tuple[int, int]]:
    """Index pairs of photos in one application that show the same picture."""
    hashed = [
        (index, inspection.difference_hash)
        for index, inspection in enumerate(inspections)
        if inspection.difference_hash is not None
    ]
    return [
        (first_index, second_index)
        for position, (first_index, first_hash) in enumerate(hashed)
        for second_index, second_hash in hashed[position + 1 :]
        if hamming_distance(first_hash, second_hash) <= max_hamming
    ]


def prepare_for_vision(content: bytes) -> tuple[bytes, str]:
    """Upright, downscaled JPEG copy without metadata, so no GPS tags leave the bank."""
    image = ImageOps.exif_transpose(_decode(content)).convert("RGB")
    image.thumbnail((VISION_MAX_EDGE_PX, VISION_MAX_EDGE_PX))
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=VISION_JPEG_QUALITY)
    return buffer.getvalue(), MEDIA_TYPE_BY_FORMAT["JPEG"]
