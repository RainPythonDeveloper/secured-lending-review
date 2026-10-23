import tomllib
from collections.abc import Iterator
from pathlib import Path

import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

from collateral_engine.domain import PropertyKind
from collateral_engine.flags import Recommendation
from collateral_engine.i18n import Language
from collateral_engine.market import write_market_data
from collateral_engine.synth import generate_sales
from collateral_engine.ui_text import UI_TEXT
from collateral_engine.vehicles.market import write_vehicle_market_data
from collateral_engine.vehicles.synth import generate_vehicle_sales

APP_PATH = Path(__file__).parents[1] / "app" / "streamlit_app.py"
STREAMLIT_CONFIG_PATH = Path(__file__).parents[1] / ".streamlit" / "config.toml"
APP_TIMEOUT_S = 180
CONSOLE_SALE_COUNT = 4000
CONSOLE_SEED = 7


@pytest.fixture(scope="module")
def console_environment(tmp_path_factory: pytest.TempPathFactory) -> Iterator[Path]:
    directory = tmp_path_factory.mktemp("console")
    market_path = directory / "comparables.csv"
    write_market_data(generate_sales(CONSOLE_SALE_COUNT, seed=CONSOLE_SEED), market_path)
    vehicle_market_path = directory / "vehicle_sales.csv"
    write_vehicle_market_data(
        generate_vehicle_sales(CONSOLE_SALE_COUNT, seed=CONSOLE_SEED), vehicle_market_path
    )
    st.cache_resource.clear()
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("COLLATERAL_MARKET_DATA_PATH", str(market_path))
        patch.setenv("COLLATERAL_VEHICLE_MARKET_DATA_PATH", str(vehicle_market_path))
        patch.setenv("COLLATERAL_AUDIT_DB_PATH", str(directory / "audit.db"))
        patch.setenv("COLLATERAL_EVIDENCE_DIR", str(directory / "evidence"))
        patch.setenv("COLLATERAL_VISION_ENABLED", "false")
        yield directory
    st.cache_resource.clear()


@pytest.fixture
def console(console_environment: Path) -> AppTest:
    app = AppTest.from_file(str(APP_PATH), default_timeout=APP_TIMEOUT_S)
    app.run()
    return app


def test_console_does_not_reload_the_cached_engine_package() -> None:
    # The engine is cached across reruns. Reloading collateral_engine after a file change mixed
    # old and new classes: "ValueError: expected the NBG rate for USD, got USD".
    server = tomllib.loads(STREAMLIT_CONFIG_PATH.read_text())["server"]

    assert "src" in server.get("folderWatchBlacklist", [])


def assess(console: AppTest) -> AppTest:
    return console.button(key="assess").click().run()


def test_console_opens_in_georgian_with_synthetic_notice(console: AppTest) -> None:
    assert not console.exception
    assert console.title[0].value == UI_TEXT["app_title"][Language.GEORGIAN]
    assert any(
        UI_TEXT["synthetic_notice"][Language.GEORGIAN] in block.value for block in console.markdown
    )


def test_console_switches_to_english(console: AppTest) -> None:
    console.radio(key="language").set_value(Language.ENGLISH).run()

    assert console.title[0].value == UI_TEXT["app_title"][Language.ENGLISH]


def test_assessing_demo_application_shows_report(console: AppTest) -> None:
    assess(console)

    report = console.session_state["report"]
    assert not console.exception
    assert report.valuation is not None
    assert report.recommendation is Recommendation.OFFICER_REVIEW


def test_report_shows_how_many_photos_are_required(console: AppTest) -> None:
    assess(console)

    assert any("0 / 3" in block.value for block in console.markdown)


def test_thin_market_demo_asks_for_physical_inspection(console: AppTest) -> None:
    console.selectbox(key="demo_case").set_value("DEMO-GLD-003").run()

    assess(console)

    assert console.session_state["report"].recommendation is Recommendation.PHYSICAL_INSPECTION


def test_accepting_flagged_valuation_without_reason_is_refused(console: AppTest) -> None:
    assess(console)

    console.button(key="record_decision").click().run()

    assert [message.value for message in console.error] == [
        UI_TEXT["reason_required"][Language.GEORGIAN]
    ]


def test_decision_with_reason_is_recorded(console: AppTest) -> None:
    assess(console)
    console.text_area(key="decision_reason").set_value("Valuer's photos checked in the branch")

    console.button(key="record_decision").click().run()

    assert console.success
    assert not console.error


def test_non_numeric_amount_is_reported_not_crashed(console: AppTest) -> None:
    console.text_input(key="field_loan_amount").set_value("two hundred")

    assess(console)

    assert not console.exception
    assert "report" not in console.session_state
    assert console.error


def test_valuer_report_tab_lists_breaches_of_84_04(console: AppTest) -> None:
    console.button(key="check_report").click().run()

    assert not console.exception
    assert any("84/04" in message.value for message in console.error)


def test_off_plan_demo_shows_stage_discount(console: AppTest) -> None:
    console.selectbox(key="demo_case").set_value("DEMO-SAB-004").run()

    assess(console)

    report = console.session_state["report"]
    assert not console.exception
    assert report.ltv is not None and report.ltv.completion_risk_factor is not None


def test_house_demo_is_valued_with_land_column(console: AppTest) -> None:
    console.selectbox(key="demo_case").set_value("DEMO-DID-005").run()

    assess(console)

    report = console.session_state["report"]
    assert not console.exception
    assert report.subject.property_kind == PropertyKind.HOUSE
    assert report.valuation is not None


def test_quality_tab_backtests_houses(console: AppTest) -> None:
    console.radio(key="quality_property_kind").set_value(PropertyKind.HOUSE).run()

    assert not console.exception


def test_vehicle_demo_is_valued_with_bank_ltv(console: AppTest) -> None:
    console.button(key="assess_vehicle").click().run()

    report = console.session_state["vehicle_report"]
    assert not console.exception
    assert report.valuation is not None
    assert report.ltv is not None


def test_vehicle_not_cleared_through_customs_needs_inspection(console: AppTest) -> None:
    console.selectbox(key="vehicle_demo_case").set_value("DEMO-CAR-003").run()

    console.button(key="assess_vehicle").click().run()

    report = console.session_state["vehicle_report"]
    assert report.recommendation is Recommendation.PHYSICAL_INSPECTION


def test_invalid_vin_is_reported_not_crashed(console: AppTest) -> None:
    console.text_input(key="vehicle_field_vin").set_value("SHORT")

    console.button(key="assess_vehicle").click().run()

    assert not console.exception
    assert "vehicle_report" not in console.session_state
    assert console.error
