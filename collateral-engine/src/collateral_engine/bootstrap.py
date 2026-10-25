"""Builds the engine and its clients from settings; the only place with side effects at startup."""

import anthropic
import httpx

from collateral_engine.audit import AuditLog
from collateral_engine.engine import CollateralEngine, EngineConfig, EngineStores
from collateral_engine.evidence import EvidenceStore
from collateral_engine.income import IteIncomeAssessor
from collateral_engine.lending.open_banking import OpenBankingClient
from collateral_engine.lending.pipeline import LoanPipeline
from collateral_engine.lending.policy import load_lending_policy, load_screening_lists
from collateral_engine.market import MarketDataError, load_market_data
from collateral_engine.nbg_rates import NbgRatesClient
from collateral_engine.nbg_rules import load_nbg_rules
from collateral_engine.nvidia_vision import NvidiaVisionClassifier
from collateral_engine.photo_registry import PhotoRegistry
from collateral_engine.policy import load_condition_rules, load_valuation_policy
from collateral_engine.settings import Settings, VisionProvider
from collateral_engine.vehicles.engine import VehicleEngine, VehicleEngineConfig
from collateral_engine.vehicles.market import VehicleMarketDataError, load_vehicle_market_data
from collateral_engine.vehicles.policy import load_vehicle_policy
from collateral_engine.vehicles.vision import VEHICLE_TASK
from collateral_engine.vision import (
    CONDITION_TASK,
    ClaudeVisionClassifier,
    PhotoClassifier,
    VisionTask,
)


def build_stores(settings: Settings) -> EngineStores:
    """One audit log, photo registry and evidence store shared by every collateral engine."""
    settings.audit_db_path.parent.mkdir(parents=True, exist_ok=True)
    return EngineStores(
        audit_log=AuditLog(settings.audit_db_path),
        photo_registry=PhotoRegistry(settings.audit_db_path),
        evidence_store=EvidenceStore(settings.evidence_dir),
    )


def build_engine(settings: Settings, stores: EngineStores) -> CollateralEngine:
    if not settings.market_data_path.exists():
        raise MarketDataError(
            f"{settings.market_data_path} not found; generate synthetic sales with "
            "'python -m collateral_engine.synth' or set COLLATERAL_MARKET_DATA_PATH"
        )
    config = EngineConfig(
        policy=load_valuation_policy(settings.config_dir / "valuation_policy.yaml"),
        condition_rules=load_condition_rules(settings.config_dir / "condition_rules.yaml"),
        nbg_rules=load_nbg_rules(settings.nbg_rules_path),
        market_data_source=settings.market_data_source,
    )
    return CollateralEngine(
        load_market_data(settings.market_data_path), config, stores, build_classifier(settings)
    )


def build_vehicle_engine(settings: Settings, stores: EngineStores) -> VehicleEngine:
    if not settings.vehicle_market_data_path.exists():
        raise VehicleMarketDataError(
            f"{settings.vehicle_market_data_path} not found; generate synthetic sales with "
            "'python -m collateral_engine.vehicles.synth' or set "
            "COLLATERAL_VEHICLE_MARKET_DATA_PATH"
        )
    config = VehicleEngineConfig(
        policy=load_vehicle_policy(settings.config_dir / "vehicle_policy.yaml"),
        market_data_source=settings.market_data_source,
    )
    market = load_vehicle_market_data(settings.vehicle_market_data_path)
    return VehicleEngine(
        market, config, stores, classifier=build_classifier(settings, VEHICLE_TASK)
    )


def build_income_assessor(settings: Settings) -> IteIncomeAssessor:
    return IteIncomeAssessor(settings.income_models_dir)


def build_loan_pipeline(
    settings: Settings,
    stores: EngineStores,
    engine: CollateralEngine,
    vehicle_engine: VehicleEngine,
) -> LoanPipeline:
    return LoanPipeline(
        rules=load_nbg_rules(settings.nbg_rules_path),
        policy=load_lending_policy(settings.config_dir / "lending_policy.yaml"),
        screening_lists=load_screening_lists(settings.config_dir / "screening_lists.yaml"),
        engine=engine,
        vehicle_engine=vehicle_engine,
        audit_log=stores.audit_log,
    )


def build_open_banking_client(settings: Settings) -> OpenBankingClient:
    return OpenBankingClient(
        httpx.Client(), settings.open_banking_gateway_url, settings.open_banking_timeout_s
    )


def build_classifier(
    settings: Settings, task: VisionTask = CONDITION_TASK
) -> PhotoClassifier | None:
    if not settings.vision_enabled:
        return None
    if settings.vision_provider is VisionProvider.NVIDIA and settings.nvidia_api_key is not None:
        return NvidiaVisionClassifier(
            httpx.Client(),
            settings.nvidia_api_key.get_secret_value(),
            settings.vision_model,
            settings.nvidia_chat_url,
            settings.vision_timeout_s,
            task=task,
        )
    client = anthropic.Anthropic(timeout=settings.vision_timeout_s)
    return ClaudeVisionClassifier(client, settings.vision_model, task)


def build_nbg_rates_client(settings: Settings) -> NbgRatesClient:
    return NbgRatesClient(httpx.Client(), settings.nbg_rates_url, settings.nbg_rates_timeout_s)
