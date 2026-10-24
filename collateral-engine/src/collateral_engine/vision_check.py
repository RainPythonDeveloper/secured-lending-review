"""Opt-in live check of the vision model on your own photos. It calls the configured provider
(COLLATERAL_VISION_PROVIDER: nvidia with NVIDIA_API_KEY, or anthropic with ANTHROPIC_API_KEY),
may be billed and is not part of the test suite.

    python -m collateral_engine.vision_check kitchen.jpg living-room.jpg
    python -m collateral_engine.vision_check --vehicle front.jpg odometer.jpg
"""

import argparse
import json
import logging
import os
from pathlib import Path

from collateral_engine.bootstrap import build_classifier
from collateral_engine.photos import prepare_for_vision
from collateral_engine.settings import load_settings
from collateral_engine.vehicles.vision import VEHICLE_TASK
from collateral_engine.vision import CONDITION_TASK

logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="Describe collateral photos with the vision model")
    parser.add_argument("photos", type=Path, nargs="+")
    parser.add_argument(
        "--vehicle", action="store_true", help="read vehicle photos instead of flat interiors"
    )
    arguments = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    settings = load_settings({**os.environ, "COLLATERAL_VISION_ENABLED": "true"})
    classifier = build_classifier(settings, VEHICLE_TASK if arguments.vehicle else CONDITION_TASK)
    logger.info("Provider %s, model %s", settings.vision_provider, settings.vision_model)
    for path in arguments.photos:
        image, media_type = prepare_for_vision(path.read_bytes())
        classification = classifier.classify(image, media_type)
        assessment = classification.assessment.model_dump() if classification.assessment else None
        failure = classification.failure.value if classification.failure else None
        result = {"photo": path.name, "assessment": assessment, "failure": failure}
        logger.info(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
