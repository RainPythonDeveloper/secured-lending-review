"""Builds the engine and its clients from settings; the only place with side effects at startup."""

import anthropic
import httpx

from collateral_engine.audit import AuditLog
from collateral_engine.engine import CollateralEngine, EngineConfig, EngineStores
from collateral_engine.evidence import EvidenceStore
from collateral_engine.market import MarketDataError, load_market_data
from collateral_engine.nbg_rates import NbgRatesClient
from collateral_engine.nbg_rules import load_nbg_rules
from collateral_engine.nvidia_vision import NvidiaConditionClassifier
from collateral_engine.photo_registry import PhotoRegistry
from collateral_engine.policy import load_condition_rules, load_valuation_policy
from collateral_engine.settings import Settings, VisionProvider
from collateral_engine.vision import ClaudeConditionClassifier, ConditionClassifier


def build_engine(settings: Settings) -> CollateralEngine:
    if not settings.market_data_path.exists():
        raise MarketDataError(
            f"{settings.market_data_path} not found; generate synthetic sales with "
            "'python -m collateral_engine.synth' or set COLLATERAL_MARKET_DATA_PATH"
        )
    settings.audit_db_path.parent.mkdir(parents=True, exist_ok=True)
    config = EngineConfig(
        policy=load_valuation_policy(settings.config_dir / "valuation_policy.yaml"),
        condition_rules=load_condition_rules(settings.config_dir / "condition_rules.yaml"),
        nbg_rules=load_nbg_rules(settings.nbg_rules_path),
        market_data_source=settings.market_data_source,
    )
    stores = EngineStores(
        audit_log=AuditLog(settings.audit_db_path),
        photo_registry=PhotoRegistry(settings.audit_db_path),
        evidence_store=EvidenceStore(settings.evidence_dir),
    )
    return CollateralEngine(
        load_market_data(settings.market_data_path), config, stores, build_classifier(settings)
    )


def build_classifier(settings: Settings) -> ConditionClassifier | None:
    if not settings.vision_enabled:
        return None
    if settings.vision_provider is VisionProvider.NVIDIA and settings.nvidia_api_key is not None:
        return NvidiaConditionClassifier(
            httpx.Client(),
            settings.nvidia_api_key.get_secret_value(),
            settings.vision_model,
            settings.nvidia_chat_url,
            settings.vision_timeout_s,
        )
    client = anthropic.Anthropic(timeout=settings.vision_timeout_s)
    return ClaudeConditionClassifier(client, settings.vision_model)


def build_nbg_rates_client(settings: Settings) -> NbgRatesClient:
    return NbgRatesClient(httpx.Client(), settings.nbg_rates_url, settings.nbg_rates_timeout_s)
