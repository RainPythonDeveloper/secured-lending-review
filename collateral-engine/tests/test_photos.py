import hashlib
import io

import pytest
from PIL import Image

from builders import encode, resized_copy, scene_photo, uniform_photo
from collateral_engine.photos import (
    PhotoQualityIssue,
    hamming_distance,
    inspect_photo,
    near_duplicate_pairs,
    prepare_for_vision,
)
from collateral_engine.policy import PhotoPolicy, ValuationPolicy


@pytest.fixture(scope="module")
def photo_policy(policy: ValuationPolicy) -> PhotoPolicy:
    return policy.photos


def test_sharp_bright_photo_is_usable(photo_policy: PhotoPolicy) -> None:
    inspection = inspect_photo(scene_photo(seed=1), photo_policy)

    assert inspection.is_usable
    assert inspection.quality_issues == ()


def test_inspection_records_sha256_of_uploaded_bytes(photo_policy: PhotoPolicy) -> None:
    content = scene_photo(seed=2)

    assert inspect_photo(content, photo_policy).sha256 == hashlib.sha256(content).hexdigest()


@pytest.mark.parametrize(
    ("content_factory", "issue"),
    [
        (lambda: uniform_photo(brightness=10), PhotoQualityIssue.TOO_DARK),
        (lambda: uniform_photo(brightness=250), PhotoQualityIssue.TOO_BRIGHT),
        (lambda: uniform_photo(brightness=128), PhotoQualityIssue.BLURRY),
        (lambda: scene_photo(seed=3, size_px=(320, 240)), PhotoQualityIssue.LOW_RESOLUTION),
        (lambda: b"not an image at all", PhotoQualityIssue.UNREADABLE),
    ],
)
def test_bad_photo_gets_quality_issue(
    photo_policy: PhotoPolicy, content_factory, issue: PhotoQualityIssue
) -> None:
    inspection = inspect_photo(content_factory(), photo_policy)

    assert issue in inspection.quality_issues
    assert not inspection.is_usable


def test_unsupported_format_is_rejected(photo_policy: PhotoPolicy) -> None:
    gif = encode(Image.new("RGB", (1024, 768), (90, 90, 90)), "GIF")

    assert inspect_photo(gif, photo_policy).quality_issues == (
        PhotoQualityIssue.UNSUPPORTED_FORMAT,
    )


def test_oversized_file_is_rejected_before_decoding(photo_policy: PhotoPolicy) -> None:
    small_limit = photo_policy.model_copy(update={"max_bytes": 100})

    assert inspect_photo(scene_photo(seed=4), small_limit).quality_issues == (
        PhotoQualityIssue.TOO_LARGE_FILE,
    )


def test_portrait_photo_is_judged_by_long_and_short_edge(photo_policy: PhotoPolicy) -> None:
    portrait = scene_photo(seed=5, size_px=(768, 1024))

    assert inspect_photo(portrait, photo_policy).is_usable


def test_resized_copy_keeps_perceptual_hash_close(photo_policy: PhotoPolicy) -> None:
    original = scene_photo(seed=6)
    first = inspect_photo(original, photo_policy)
    second = inspect_photo(resized_copy(original, 0.7), photo_policy)

    assert first.sha256 != second.sha256
    assert hamming_distance(first.difference_hash, second.difference_hash) <= 6


def test_different_scenes_have_distant_hashes(photo_policy: PhotoPolicy) -> None:
    first = inspect_photo(scene_photo(seed=7), photo_policy)
    second = inspect_photo(scene_photo(seed=8), photo_policy)

    assert hamming_distance(first.difference_hash, second.difference_hash) > 6


def test_near_duplicate_pairs_finds_resubmitted_photo(photo_policy: PhotoPolicy) -> None:
    original = scene_photo(seed=9)
    inspections = [
        inspect_photo(original, photo_policy),
        inspect_photo(scene_photo(seed=10), photo_policy),
        inspect_photo(resized_copy(original, 0.8), photo_policy),
    ]

    assert near_duplicate_pairs(inspections, max_hamming=6) == [(0, 2)]


def test_prepare_for_vision_downscales_and_strips_metadata() -> None:
    exif = Image.Exif()
    exif[0x010F] = "Camera maker that must not leave the bank"
    large = Image.new("RGB", (4000, 3000), (120, 120, 120))
    buffer = io.BytesIO()
    large.save(buffer, format="JPEG", exif=exif)

    prepared, media_type = prepare_for_vision(buffer.getvalue())
    image = Image.open(io.BytesIO(prepared))

    assert media_type == "image/jpeg"
    assert max(image.size) == 1568
    assert len(image.getexif()) == 0
