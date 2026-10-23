from collections.abc import Callable
from datetime import timedelta
from pathlib import Path

import pytest

from collateral_engine.audit import AuditLog
from collateral_engine.domain import PropertyKind
from collateral_engine.engine import CollateralEngine, EngineConfig, EngineStores
from collateral_engine.evidence import EvidenceStore
from collateral_engine.market import MarketData
from collateral_engine.nbg_rules import (
    NbgRules,
    ValuationLimits,
    load_nbg_rules,
    rule_version_in_force,
)
from collateral_engine.photo_registry import PhotoRegistry
from collateral_engine.policy import (
    ConditionRules,
    ValuationPolicy,
    load_condition_rules,
    load_valuation_policy,
)
from collateral_engine.settings import DEFAULT_NBG_RULES_PATH
from collateral_engine.synth import generate_sales
from collateral_engine.valuation import IntervalCalibration, calibrate_interval
from collateral_engine.vehicles.engine import VehicleEngine, VehicleEngineConfig
from collateral_engine.vehicles.market import VehicleMarketData
from collateral_engine.vehicles.policy import VehiclePolicy, load_vehicle_policy
from collateral_engine.vehicles.synth import generate_vehicle_sales
from collateral_engine.vehicles.valuation import (
    VehicleIntervalCalibration,
    calibrate_vehicle_interval,
)
from collateral_engine.vision import ConditionClassifier

TEST_SEED = 7
TEST_SALE_COUNT = 4000
FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def market() -> MarketData:
    return MarketData.from_sales(generate_sales(TEST_SALE_COUNT, seed=TEST_SEED))


@pytest.fixture(scope="session")
def policy() -> ValuationPolicy:
    return load_valuation_policy()


@pytest.fixture(scope="session")
def condition_rules() -> ConditionRules:
    return load_condition_rules()


@pytest.fixture(scope="session")
def nbg_rules() -> NbgRules:
    return load_nbg_rules(DEFAULT_NBG_RULES_PATH)


@pytest.fixture(scope="session")
def limits(nbg_rules: NbgRules, market: MarketData) -> ValuationLimits:
    return rule_version_in_force(nbg_rules, market.last_sale_date).valuation


@pytest.fixture(scope="session")
def calibration(
    market: MarketData, policy: ValuationPolicy, limits: ValuationLimits
) -> IntervalCalibration:
    return calibrate_interval(market, market.last_sale_date + timedelta(days=1), policy, limits)


@pytest.fixture(scope="session")
def house_calibration(
    market: MarketData, policy: ValuationPolicy, limits: ValuationLimits
) -> IntervalCalibration:
    return calibrate_interval(
        market, market.last_sale_date + timedelta(days=1), policy, limits, PropertyKind.HOUSE
    )


@pytest.fixture
def stores(tmp_path: Path) -> EngineStores:
    database = tmp_path / "audit.db"
    return EngineStores(
        audit_log=AuditLog(database),
        photo_registry=PhotoRegistry(database),
        evidence_store=EvidenceStore(tmp_path / "evidence"),
    )


@pytest.fixture
def make_engine(
    market: MarketData,
    policy: ValuationPolicy,
    condition_rules: ConditionRules,
    nbg_rules: NbgRules,
    calibration: IntervalCalibration,
    house_calibration: IntervalCalibration,
    stores: EngineStores,
) -> Callable[[ConditionClassifier | None], CollateralEngine]:
    config = EngineConfig(policy, condition_rules, nbg_rules, "synthetic test sales")

    def build(classifier: ConditionClassifier | None = None) -> CollateralEngine:
        calibrations = {PropertyKind.FLAT: calibration, PropertyKind.HOUSE: house_calibration}
        return CollateralEngine(market, config, stores, classifier, calibrations)

    return build


VEHICLE_TEST_SALE_COUNT = 4000


@pytest.fixture(scope="session")
def vehicle_market() -> VehicleMarketData:
    return VehicleMarketData.from_sales(
        generate_vehicle_sales(VEHICLE_TEST_SALE_COUNT, seed=TEST_SEED)
    )


@pytest.fixture(scope="session")
def vehicle_policy() -> VehiclePolicy:
    return load_vehicle_policy()


@pytest.fixture(scope="session")
def vehicle_calibration(
    vehicle_market: VehicleMarketData, vehicle_policy: VehiclePolicy
) -> VehicleIntervalCalibration:
    window_end = vehicle_market.last_sale_date + timedelta(days=1)
    return calibrate_vehicle_interval(vehicle_market, window_end, vehicle_policy)


@pytest.fixture
def make_vehicle_engine(
    vehicle_market: VehicleMarketData,
    vehicle_policy: VehiclePolicy,
    vehicle_calibration: VehicleIntervalCalibration,
    stores: EngineStores,
) -> Callable[[], VehicleEngine]:
    config = VehicleEngineConfig(vehicle_policy, "synthetic test vehicle sales")

    def build() -> VehicleEngine:
        return VehicleEngine(vehicle_market, config, stores, vehicle_calibration)

    return build
