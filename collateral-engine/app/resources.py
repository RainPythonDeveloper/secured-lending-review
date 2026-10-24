"""Engines and clients shared by every page of the console, built once per server process."""

from datetime import date
from decimal import Decimal

import streamlit as st

from collateral_engine.bootstrap import (
    build_engine,
    build_loan_pipeline,
    build_nbg_rates_client,
    build_open_banking_client,
    build_stores,
    build_vehicle_engine,
)
from collateral_engine.engine import CollateralEngine, EngineStores
from collateral_engine.lending.bank_data import BankSnapshot, load_bank_snapshot
from collateral_engine.lending.open_banking import OpenBankingClient
from collateral_engine.lending.pipeline import LoanPipeline
from collateral_engine.nbg_rates import NbgRatesClient, OfficialRateUnavailableError
from collateral_engine.settings import load_settings
from collateral_engine.vehicles.engine import VehicleEngine

STATEMENT_CURRENCIES = ("USD", "EUR")
STATEMENT_RATES_TTL_S = 3600
# Shown while an engine loads for the first time; the language is not known at that point.
LOADING_ENGINES = "ძრავების ჩატვირთვა… · Loading the engines…"


@st.cache_resource(show_spinner=False)
def get_stores() -> EngineStores:
    return build_stores(load_settings())


@st.cache_resource(show_spinner=LOADING_ENGINES)
def get_engine() -> CollateralEngine:
    return build_engine(load_settings(), get_stores())


@st.cache_resource(show_spinner=LOADING_ENGINES)
def get_vehicle_engine() -> VehicleEngine:
    return build_vehicle_engine(load_settings(), get_stores())


@st.cache_resource(show_spinner=False)
def get_rates_client() -> NbgRatesClient:
    return build_nbg_rates_client(load_settings())


@st.cache_resource(show_spinner=LOADING_ENGINES)
def get_loan_pipeline() -> LoanPipeline:
    settings = load_settings()
    return build_loan_pipeline(settings, get_stores(), get_engine(), get_vehicle_engine())


@st.cache_resource(show_spinner=False)
def get_bank_snapshot() -> BankSnapshot:
    return load_bank_snapshot(load_settings().bank_dataset_path)


@st.cache_resource(show_spinner=False)
def get_open_banking_client() -> OpenBankingClient:
    return build_open_banking_client(load_settings())


@st.cache_data(show_spinner=False, ttl=STATEMENT_RATES_TTL_S)
def get_statement_rates(rate_date: date) -> dict[str, Decimal]:
    """NBG rates of the foreign currencies in the statements; a currency NBG cannot give is left
    out, and its inflows are then not counted as income."""
    rates: dict[str, Decimal] = {}
    for code in STATEMENT_CURRENCIES:
        try:
            rates[code] = get_rates_client().fetch_gel_per_unit(code, rate_date)
        except OfficialRateUnavailableError:
            continue
    return rates
