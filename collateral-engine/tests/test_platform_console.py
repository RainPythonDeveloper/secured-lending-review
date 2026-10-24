"""The unified console: full application, collateral and income pages in one app.

The full application runs the trained income engine, which `make data` builds in income-engine/.
"""

from collections.abc import Iterator
from pathlib import Path

import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

from collateral_engine.full_application import FullApplicationRecommendation
from collateral_engine.i18n import Language
from collateral_engine.market import write_market_data
from collateral_engine.settings import INCOME_ENGINE_ROOT
from collateral_engine.synth import generate_sales
from collateral_engine.ui_text import UI_TEXT
from collateral_engine.vehicles.market import write_vehicle_market_data
from collateral_engine.vehicles.synth import generate_vehicle_sales
from language import LANGUAGE_WIDGET_KEY

PLATFORM_PATH = Path(__file__).parents[1] / "app" / "platform_app.py"
APP_TIMEOUT_S = 300
SALE_COUNT = 4000
SEED = 7


@pytest.fixture(scope="module")
def platform_environment(tmp_path_factory: pytest.TempPathFactory) -> Iterator[Path]:
    directory = tmp_path_factory.mktemp("platform")
    write_market_data(generate_sales(SALE_COUNT, seed=SEED), directory / "comparables.csv")
    write_vehicle_market_data(
        generate_vehicle_sales(SALE_COUNT, seed=SEED), directory / "vehicle_sales.csv"
    )
    st.cache_resource.clear()
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("COLLATERAL_MARKET_DATA_PATH", str(directory / "comparables.csv"))
        patch.setenv("COLLATERAL_VEHICLE_MARKET_DATA_PATH", str(directory / "vehicle_sales.csv"))
        patch.setenv("COLLATERAL_AUDIT_DB_PATH", str(directory / "audit.db"))
        patch.setenv("COLLATERAL_EVIDENCE_DIR", str(directory / "evidence"))
        patch.setenv("COLLATERAL_VISION_ENABLED", "false")
        yield directory
    st.cache_resource.clear()


@pytest.fixture
def console(platform_environment: Path) -> AppTest:
    app = AppTest.from_file(str(PLATFORM_PATH), default_timeout=APP_TIMEOUT_S)
    app.run()
    return app


def test_platform_opens_on_the_full_application(console: AppTest) -> None:
    assert not console.exception
    assert console.title[0].value == UI_TEXT["full_title"][Language.GEORGIAN]


def test_full_application_combines_income_and_collateral(console: AppTest) -> None:
    console.button(key="assess_full").click().run()

    report = console.session_state["full_report"]
    assert not console.exception
    assert report.offer_amount_gel <= report.max_by_income_gel


def test_full_application_with_a_vehicle(console: AppTest) -> None:
    console.radio(key="full_is_vehicle").set_value(True).run()

    console.button(key="assess_full").click().run()

    report = console.session_state["full_report"]
    assert report.vehicle is not None
    assert report.recommendation in set(FullApplicationRecommendation)


def test_full_application_labels_do_not_change_with_language(console: AppTest) -> None:
    georgian_labels = console.selectbox(key="full_borrower").options

    console.radio(key=LANGUAGE_WIDGET_KEY).set_value(Language.ENGLISH).run()

    assert console.selectbox(key="full_borrower").options == georgian_labels


def test_collateral_page_runs_inside_the_platform(console: AppTest) -> None:
    console.switch_page("streamlit_app.py").run()

    assert not console.exception
    assert console.title[0].value == UI_TEXT["app_title"][Language.GEORGIAN]


def test_income_page_runs_inside_the_platform(console: AppTest) -> None:
    console.switch_page(str(INCOME_ENGINE_ROOT / "app" / "streamlit_app.py")).run()

    assert not console.exception


def test_missing_income_models_are_reported_not_crashed(
    console: AppTest, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("INCOME_MODELS_DIR", str(tmp_path))
    st.cache_resource.clear()

    console.button(key="assess_full").click().run()

    assert not console.exception
    assert "full_report" not in console.session_state
    assert console.error


def test_language_chosen_once_applies_to_every_page(console: AppTest) -> None:
    console.radio(key=LANGUAGE_WIDGET_KEY).set_value(Language.ENGLISH).run()

    console.switch_page("streamlit_app.py").run()

    assert console.title[0].value == UI_TEXT["app_title"][Language.ENGLISH]


def test_language_survives_a_round_trip_between_pages(console: AppTest) -> None:
    console.switch_page("streamlit_app.py").run()
    console.radio(key=LANGUAGE_WIDGET_KEY).set_value(Language.ENGLISH).run()

    console.switch_page("full_application_page.py").run()

    assert console.title[0].value == UI_TEXT["full_title"][Language.ENGLISH]
