"""Engines and clients shared by every page of the console, built once per server process."""

import streamlit as st

from collateral_engine.bootstrap import (
    build_engine,
    build_income_assessor,
    build_nbg_rates_client,
    build_stores,
    build_vehicle_engine,
)
from collateral_engine.engine import CollateralEngine, EngineStores
from collateral_engine.income import IteIncomeAssessor
from collateral_engine.nbg_rates import NbgRatesClient
from collateral_engine.settings import load_settings
from collateral_engine.vehicles.engine import VehicleEngine


@st.cache_resource(show_spinner=False)
def get_stores() -> EngineStores:
    return build_stores(load_settings())


@st.cache_resource(show_spinner=False)
def get_engine() -> CollateralEngine:
    return build_engine(load_settings(), get_stores())


@st.cache_resource(show_spinner=False)
def get_vehicle_engine() -> VehicleEngine:
    return build_vehicle_engine(load_settings(), get_stores())


@st.cache_resource(show_spinner=False)
def get_income_assessor() -> IteIncomeAssessor:
    return build_income_assessor(load_settings())


@st.cache_resource(show_spinner=False)
def get_rates_client() -> NbgRatesClient:
    return build_nbg_rates_client(load_settings())
