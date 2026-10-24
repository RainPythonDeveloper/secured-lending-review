from pathlib import Path
from string import Formatter

import pytest
import yaml
from pydantic import ValidationError

from collateral_engine.demo_cases import DEMO_CASES
from collateral_engine.domain import BuildingStatus, ClaimStatus, Condition
from collateral_engine.flags import Flag, ReasonCode, Recommendation, Severity
from collateral_engine.full_application import BindingLimit, FullApplicationRecommendation
from collateral_engine.i18n import (
    BINDING_LIMIT_NAMES,
    BUILDING_STATUS_NAMES,
    CLAIM_STATUS_NAMES,
    CONDITION_NAMES,
    FUEL_TYPE_NAMES,
    FULL_APPLICATION_RECOMMENDATION_NAMES,
    INCOME_RECOMMENDATION_NAMES,
    REASON_TEMPLATES,
    RECOMMENDATION_NAMES,
    STEERING_SIDE_NAMES,
    VEHICLE_ADJUSTMENT_NAMES,
    Language,
    reason_text,
)
from collateral_engine.income import IncomeRecommendation
from collateral_engine.nvidia_vision import DEFAULT_NVIDIA_VISION_MODEL
from collateral_engine.policy import (
    DEFAULT_CONFIG_DIR,
    ConditionRules,
    ValuationPolicy,
)
from collateral_engine.settings import SettingsError, VisionProvider, load_settings
from collateral_engine.vehicles.domain import FuelType, SteeringSide
from collateral_engine.vehicles.report import VehicleAdjustmentGroup


@pytest.mark.parametrize(
    ("names", "members"),
    [
        (CONDITION_NAMES, Condition),
        (BUILDING_STATUS_NAMES, BuildingStatus),
        (CLAIM_STATUS_NAMES, ClaimStatus),
        (RECOMMENDATION_NAMES, Recommendation),
        (REASON_TEMPLATES, ReasonCode),
        (FUEL_TYPE_NAMES, FuelType),
        (STEERING_SIDE_NAMES, SteeringSide),
        (VEHICLE_ADJUSTMENT_NAMES, VehicleAdjustmentGroup),
        (INCOME_RECOMMENDATION_NAMES, IncomeRecommendation),
        (FULL_APPLICATION_RECOMMENDATION_NAMES, FullApplicationRecommendation),
        (BINDING_LIMIT_NAMES, BindingLimit),
    ],
)
def test_every_value_has_georgian_and_english_text(names: dict, members) -> None:
    assert set(names) == set(members)
    assert all(names[member][language] for member in members for language in Language)


def test_georgian_and_english_templates_use_the_same_placeholders() -> None:
    def placeholders(template: str) -> set[str]:
        return {name for _, name, _, _ in Formatter().parse(template) if name}

    mismatched = [
        code
        for code, texts in REASON_TEMPLATES.items()
        if placeholders(texts[Language.GEORGIAN]) != placeholders(texts[Language.ENGLISH])
    ]
    assert mismatched == []


def test_reason_text_names_condition_in_chosen_language() -> None:
    flag = Flag(
        code=ReasonCode.CONDITION_CONTRADICTED,
        severity=Severity.PHYSICAL_INSPECTION,
        params={"declared": "newly_renovated", "observed": "black_frame"},
    )

    assert "შავი კარკასი" in reason_text(flag, Language.GEORGIAN)
    assert "Black frame" in reason_text(flag, Language.ENGLISH)


def test_policy_must_give_every_reason_a_severity() -> None:
    document = yaml.safe_load((DEFAULT_CONFIG_DIR / "valuation_policy.yaml").read_text())
    del document["flag_severity"]["MODEL_DISAGREEMENT"]

    with pytest.raises(ValidationError, match="MODEL_DISAGREEMENT"):
        ValuationPolicy.model_validate(document)


def test_policy_rejects_unknown_keys() -> None:
    document = yaml.safe_load((DEFAULT_CONFIG_DIR / "valuation_policy.yaml").read_text())
    document["comparables"]["search_radius_miles"] = 1

    with pytest.raises(ValidationError):
        ValuationPolicy.model_validate(document)


def test_condition_rules_must_rank_every_condition() -> None:
    document = yaml.safe_load((DEFAULT_CONFIG_DIR / "condition_rules.yaml").read_text())
    del document["finish_levels"]["green_frame"]

    with pytest.raises(ValidationError, match="green_frame"):
        ConditionRules.model_validate(document)


def test_condition_rules_cannot_count_more_photos_than_required() -> None:
    document = yaml.safe_load((DEFAULT_CONFIG_DIR / "condition_rules.yaml").read_text())
    document["min_classified_photos"] = document["min_photos"] + 1

    with pytest.raises(ValidationError, match="min_classified_photos"):
        ConditionRules.model_validate(document)


def test_settings_default_to_vision_off_and_repository_nbg_rules() -> None:
    settings = load_settings({})

    assert not settings.vision_enabled
    assert settings.nbg_rules_path.exists()


def test_settings_read_environment() -> None:
    settings = load_settings(
        {
            "COLLATERAL_VISION_ENABLED": "true",
            "COLLATERAL_VISION_PROVIDER": "anthropic",
            "COLLATERAL_AUDIT_DB_PATH": "/tmp/x.db",
        }
    )

    assert settings.vision_enabled
    assert settings.audit_db_path == Path("/tmp/x.db")


def test_settings_default_to_nvidia_model() -> None:
    settings = load_settings({})

    assert settings.vision_provider is VisionProvider.NVIDIA
    assert settings.vision_model == DEFAULT_NVIDIA_VISION_MODEL


def test_settings_require_nvidia_key_when_nvidia_vision_is_on() -> None:
    with pytest.raises(SettingsError, match="NVIDIA_API_KEY"):
        load_settings({"COLLATERAL_VISION_ENABLED": "true", "COLLATERAL_VISION_PROVIDER": "nvidia"})


def test_settings_keep_nvidia_key_secret() -> None:
    settings = load_settings({"NVIDIA_API_KEY": "nvapi-secret"})

    assert "nvapi-secret" not in repr(settings)
    assert settings.nvidia_api_key.get_secret_value() == "nvapi-secret"


def test_empty_variables_from_env_file_mean_default() -> None:
    settings = load_settings({"COLLATERAL_CONFIG_DIR": "", "NVIDIA_API_KEY": ""})

    assert settings.config_dir == load_settings({}).config_dir
    assert settings.nvidia_api_key is None


def test_settings_reject_unknown_provider() -> None:
    with pytest.raises(SettingsError):
        load_settings({"COLLATERAL_VISION_PROVIDER": "openai"})


def test_settings_reject_invalid_timeout() -> None:
    with pytest.raises(SettingsError):
        load_settings({"NBG_RATES_TIMEOUT_S": "-1"})


def test_demo_cases_are_invented_and_bilingual() -> None:
    assert all(case.application_id.startswith("DEMO-") for case in DEMO_CASES)
    assert all(case.title[language] for case in DEMO_CASES for language in Language)
