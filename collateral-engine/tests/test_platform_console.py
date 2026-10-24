"""The console: the overview and the loan application pipeline, collateral included.

No test reaches the network: the Open Banking gateway and the NBG rate API point at a closed port,
which also exercises the fallback to the bank's records.
"""

import tomllib
from collections.abc import Iterator
from pathlib import Path

import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

from builders import make_vehicle
from collateral_engine.demo_cases import DEMO_CASES
from collateral_engine.domain import PropertyKind
from collateral_engine.i18n import Language
from collateral_engine.lending.affordability import LoanProduct
from collateral_engine.lending.customer import DataSource
from collateral_engine.lending.decision import LoanDecisionKind
from collateral_engine.lending.pipeline import LendingRecommendation
from collateral_engine.lending.policy import load_lending_policy
from collateral_engine.market import write_market_data
from collateral_engine.synth import generate_sales
from collateral_engine.ui_text import UI_TEXT
from collateral_engine.vehicles.demo_cases import VEHICLE_DEMO_CASES
from collateral_engine.vehicles.evidence import check_vehicle_evidence, photo_reading
from collateral_engine.vehicles.market import write_vehicle_market_data
from collateral_engine.vehicles.synth import generate_vehicle_sales
from collateral_engine.vehicles.vision import (
    SteeringReading,
    VehiclePhotoAssessment,
    VehicleView,
    VisibleDamage,
)
from collateral_engine.vision import PhotoClassification, VisionConfidence
from collateral_form import CollateralMode
from collateral_view import views_found_text
from language import LANGUAGE_WIDGET_KEY, choice_widget_key

PLATFORM_PATH = Path(__file__).parents[1] / "app" / "platform_app.py"
APPLICATION_PAGE = "application_page.py"
OVERVIEW_PAGE = "overview_page.py"
STREAMLIT_CONFIG_PATH = Path(__file__).parents[1] / ".streamlit" / "config.toml"
APP_TIMEOUT_S = 300
SALE_COUNT = 4000
SEED = 7
CLOSED_PORT_URL = "http://127.0.0.1:9"
DEBTOR_CUSTOMER = "CUS-017"
THIN_MARKET_CASE = "DEMO-GLD-003"
OFF_PLAN_CASE = "DEMO-SAB-004"
HOUSE_CASE = "DEMO-DID-005"
NOT_CLEARED_CAR = "DEMO-CAR-003"
EDITED_AREA_M2 = 120.0


@pytest.fixture(scope="module")
def platform_environment(tmp_path_factory: pytest.TempPathFactory) -> Iterator[Path]:
    directory = tmp_path_factory.mktemp("platform")
    write_market_data(generate_sales(SALE_COUNT, seed=SEED), directory / "comparables.csv")
    write_vehicle_market_data(
        generate_vehicle_sales(SALE_COUNT, seed=SEED), directory / "vehicle_sales.csv"
    )
    st.cache_resource.clear()
    st.cache_data.clear()
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("COLLATERAL_MARKET_DATA_PATH", str(directory / "comparables.csv"))
        patch.setenv("COLLATERAL_VEHICLE_MARKET_DATA_PATH", str(directory / "vehicle_sales.csv"))
        patch.setenv("COLLATERAL_AUDIT_DB_PATH", str(directory / "audit.db"))
        patch.setenv("COLLATERAL_EVIDENCE_DIR", str(directory / "evidence"))
        patch.setenv("COLLATERAL_VISION_ENABLED", "false")
        patch.setenv("OPEN_BANKING_GATEWAY_URL", CLOSED_PORT_URL)
        patch.setenv("OPEN_BANKING_TIMEOUT_S", "2")
        patch.setenv("NBG_RATES_URL", CLOSED_PORT_URL)
        patch.setenv("NBG_RATES_TIMEOUT_S", "2")
        yield directory
    st.cache_resource.clear()
    st.cache_data.clear()


@pytest.fixture
def console(platform_environment: Path) -> AppTest:
    app = AppTest.from_file(str(PLATFORM_PATH), default_timeout=APP_TIMEOUT_S)
    app.run()
    return app


@pytest.fixture
def application(console: AppTest) -> AppTest:
    console.switch_page(APPLICATION_PAGE).run()
    return console


def georgian(key: str) -> str:
    return choice_widget_key(key, Language.GEORGIAN)


def page_html(app: AppTest) -> str:
    return " ".join(block.value for block in app.markdown)


def load_bank_records(app: AppTest) -> AppTest:
    return app.button(key="loan_bank_records").click().run()


def run_checks(app: AppTest) -> AppTest:
    return app.button(key="loan_run_checks").click().run()


def choose_product(app: AppTest, product: LoanProduct) -> AppTest:
    return app.radio(key=georgian("loan_product")).set_value(product).run()


def fill_in_myself(app: AppTest) -> AppTest:
    return app.radio(key=georgian("collateral_mode")).set_value(CollateralMode.MANUAL).run()


def collateral_report(app: AppTest) -> object:
    report = app.session_state["loan_report"]
    return report.real_estate_report or report.vehicle_report


def test_console_does_not_reload_the_cached_engine_package() -> None:
    # The engine is cached across reruns. Reloading collateral_engine after a file change mixed
    # old and new classes: "ValueError: expected the NBG rate for USD, got USD".
    server = tomllib.loads(STREAMLIT_CONFIG_PATH.read_text())["server"]

    assert "src" in server.get("folderWatchBlacklist", [])


def test_platform_opens_on_the_overview(console: AppTest) -> None:
    assert not console.exception
    assert UI_TEXT["product_name"][Language.GEORGIAN] in page_html(console)


def test_overview_explains_the_four_steps(console: AppTest) -> None:
    html = page_html(console)

    assert all(UI_TEXT[f"step{number}_title"][Language.GEORGIAN] in html for number in (1, 2, 3, 4))


def test_checks_wait_for_the_applicant_data(application: AppTest) -> None:
    assert application.button(key="loan_run_checks").disabled


def test_bank_records_feed_the_whole_pipeline(application: AppTest) -> None:
    run_checks(load_bank_records(application))

    report = application.session_state["loan_report"]
    assert not application.exception
    assert report.data_source is DataSource.BANK_SNAPSHOT
    assert report.recommendation is LendingRecommendation.OFFER


def test_rerunning_the_checks_keeps_the_application_number(application: AppTest) -> None:
    # A new number on every run made the applicant's own photos look reused from another
    # application, which asks for a physical inspection.
    run_checks(load_bank_records(application))
    first_number = application.session_state["loan_report"].application_id

    run_checks(application)

    assert application.session_state["loan_report"].application_id == first_number


def test_another_applicant_gets_a_new_application_number(application: AppTest) -> None:
    run_checks(load_bank_records(application))
    first_number = application.session_state["loan_report"].application_id
    application.selectbox(key=georgian("loan_customer_id")).set_value(DEBTOR_CUSTOMER).run()

    run_checks(load_bank_records(application))

    assert application.session_state["loan_report"].application_id != first_number


def test_unreachable_gateway_is_reported_with_the_fallback_offered(application: AppTest) -> None:
    application.button(key="loan_ob_request").click().run()

    assert not application.exception
    assert application.warning
    assert application.button(key="loan_bank_records")


def test_bank_records_drop_the_pending_consent_prompt(application: AppTest) -> None:
    application.session_state["loan_consent_pending"] = True

    load_bank_records(application)

    assert not application.info


def test_new_applicant_is_generated_and_assessed(application: AppTest) -> None:
    application.radio(key=georgian("loan_is_existing")).set_value(False).run()
    application.button(key="loan_generate").click().run()

    run_checks(application)

    report = application.session_state["loan_report"]
    assert report.data_source is DataSource.SYNTHETIC_APPLICANT


def test_mortgage_values_the_flat(application: AppTest) -> None:
    load_bank_records(application)
    application.radio(key=georgian("loan_product")).set_value(LoanProduct.MORTGAGE).run()

    run_checks(application)

    report = application.session_state["loan_report"]
    assert report.real_estate_report is not None
    assert report.max_by_collateral_gel is not None


def test_debtors_registry_record_goes_to_the_officer(application: AppTest) -> None:
    application.selectbox(key=georgian("loan_customer_id")).set_value(DEBTOR_CUSTOMER).run()

    run_checks(load_bank_records(application))

    assert application.session_state["loan_report"].recommendation is (
        LendingRecommendation.OFFICER_REVIEW
    )


def test_decision_form_starts_from_the_recommendation(application: AppTest) -> None:
    application.selectbox(key=georgian("loan_customer_id")).set_value(DEBTOR_CUSTOMER).run()

    run_checks(load_bank_records(application))

    decision_kind = application.radio(key=georgian("loan_decision_kind")).value
    assert decision_kind is LoanDecisionKind.REQUEST_DOCUMENTS


def test_officer_decision_is_recorded(application: AppTest) -> None:
    run_checks(load_bank_records(application))

    application.button(key="loan_record_decision").click().run()

    assert not application.exception
    assert application.success


def test_decline_without_reason_is_refused(application: AppTest) -> None:
    run_checks(load_bank_records(application))
    # Inside a form the value is sent with the submit button, so no run in between.
    application.radio(key=georgian("loan_decision_kind")).set_value(LoanDecisionKind.DECLINE)

    application.button(key="loan_record_decision").click().run()

    assert application.error


def test_language_switch_keeps_the_loaded_application(application: AppTest) -> None:
    run_checks(load_bank_records(application))

    application.radio(key=LANGUAGE_WIDGET_KEY).set_value(Language.ENGLISH).run()

    assert application.session_state["loan_report"] is not None
    assert application.title[0].value == UI_TEXT["loan_title"][Language.ENGLISH]


def test_language_chosen_once_applies_to_every_page(console: AppTest) -> None:
    console.radio(key=LANGUAGE_WIDGET_KEY).set_value(Language.ENGLISH).run()

    console.switch_page(APPLICATION_PAGE).run()

    assert console.title[0].value == UI_TEXT["loan_title"][Language.ENGLISH]


def test_language_survives_a_round_trip_between_pages(application: AppTest) -> None:
    application.radio(key=LANGUAGE_WIDGET_KEY).set_value(Language.ENGLISH).run()
    application.switch_page(OVERVIEW_PAGE).run()

    application.switch_page(APPLICATION_PAGE).run()

    assert application.title[0].value == UI_TEXT["loan_title"][Language.ENGLISH]


def test_mortgage_report_shows_how_many_photos_are_required(application: AppTest) -> None:
    choose_product(load_bank_records(application), LoanProduct.MORTGAGE)

    run_checks(application)

    assert any("0 / 3" in block.value for block in application.markdown)


def test_thin_market_case_asks_for_physical_inspection(application: AppTest) -> None:
    choose_product(load_bank_records(application), LoanProduct.MORTGAGE)
    application.radio(key=georgian("loan_real_estate_case")).set_value(THIN_MARKET_CASE).run()

    run_checks(application)

    assert application.session_state["loan_report"].recommendation is (
        LendingRecommendation.PHYSICAL_INSPECTION
    )


def test_off_plan_case_shows_the_construction_stage_discount(application: AppTest) -> None:
    choose_product(load_bank_records(application), LoanProduct.MORTGAGE)
    application.radio(key=georgian("loan_real_estate_case")).set_value(OFF_PLAN_CASE).run()

    run_checks(application)

    ltv = collateral_report(application).ltv
    assert ltv is not None and ltv.completion_risk_factor is not None


def test_house_case_is_valued_as_a_house(application: AppTest) -> None:
    choose_product(load_bank_records(application), LoanProduct.MORTGAGE)
    application.radio(key=georgian("loan_real_estate_case")).set_value(HOUSE_CASE).run()

    run_checks(application)

    valuation_report = collateral_report(application)
    assert not application.exception
    assert valuation_report.subject.property_kind is PropertyKind.HOUSE
    assert valuation_report.valuation is not None


def test_car_loan_is_valued_with_the_bank_ltv(application: AppTest) -> None:
    choose_product(load_bank_records(application), LoanProduct.AUTO)

    run_checks(application)

    assert not application.exception
    assert collateral_report(application).ltv is not None


def test_product_starts_from_the_bank_policy_amount(application: AppTest) -> None:
    choose_product(application, LoanProduct.MORTGAGE)

    expected = load_lending_policy().products.mortgage.default_amount_gel
    assert application.number_input(key="loan_amount").value == float(expected)


def test_car_ltv_is_labelled_as_bank_policy_not_nbg(application: AppTest) -> None:
    run_checks(choose_product(load_bank_records(application), LoanProduct.AUTO))

    html = page_html(application)
    assert UI_TEXT["ltv_bank_limit"][Language.GEORGIAN] in html
    assert UI_TEXT["ltv"][Language.GEORGIAN] not in html


def test_views_found_count_only_the_required_views(vehicle_policy) -> None:
    required = vehicle_policy.vision.required_views
    readings = [
        photo_reading(
            f"sha-{view}",
            PhotoClassification(
                VehiclePhotoAssessment(
                    shows_vehicle=True,
                    contains_people=False,
                    view=view,
                    odometer_reading=None,
                    odometer_unit=None,
                    vin=None,
                    damage=VisibleDamage.NONE,
                    steering_side=SteeringReading.LEFT,
                    confidence=VisionConfidence.HIGH,
                    visible_evidence=[],
                ),
                None,
            ),
            vehicle_policy.vision,
        )
        for view in (VehicleView.INTERIOR, VehicleView.FRONT)
    ]
    evidence = check_vehicle_evidence(make_vehicle(), readings, vehicle_policy.vision)

    assert views_found_text(evidence, len(required)) == f"1 / {len(required)}"


def test_car_not_cleared_through_customs_needs_inspection(application: AppTest) -> None:
    choose_product(load_bank_records(application), LoanProduct.AUTO)
    application.radio(key=georgian("loan_vehicle_case")).set_value(NOT_CLEARED_CAR).run()

    run_checks(application)

    assert application.session_state["loan_report"].recommendation is (
        LendingRecommendation.PHYSICAL_INSPECTION
    )


def test_manual_form_starts_from_the_chosen_case(application: AppTest) -> None:
    choose_product(application, LoanProduct.MORTGAGE)
    case = DEMO_CASES[1]
    application.radio(key=georgian("loan_real_estate_case")).set_value(case.application_id).run()

    fill_in_myself(application)

    cadastral_code = application.text_input(key="collateral_estate_cadastral_code").value
    assert cadastral_code == case.subject.cadastral_code


def test_edited_field_reaches_the_valuation(application: AppTest) -> None:
    fill_in_myself(choose_product(load_bank_records(application), LoanProduct.MORTGAGE))
    application.number_input(key="collateral_estate_total_area_m2").set_value(EDITED_AREA_M2)

    run_checks(application)

    assert collateral_report(application).subject.total_area_m2 == EDITED_AREA_M2


def test_typed_fields_survive_a_switch_to_the_demo_case_and_back(application: AppTest) -> None:
    fill_in_myself(choose_product(application, LoanProduct.MORTGAGE))
    application.number_input(key="collateral_estate_total_area_m2").set_value(EDITED_AREA_M2).run()
    application.radio(key=georgian("collateral_mode")).set_value(CollateralMode.DEMO).run()

    fill_in_myself(application)

    assert application.number_input(key="collateral_estate_total_area_m2").value == EDITED_AREA_M2


def test_invalid_vin_is_reported_not_crashed(application: AppTest) -> None:
    fill_in_myself(choose_product(load_bank_records(application), LoanProduct.AUTO))
    application.text_input(key="collateral_vehicle_vin").set_value("SHORT")

    run_checks(application)

    assert not application.exception
    assert "loan_report" not in application.session_state
    assert application.error


def test_valuer_report_check_lists_breaches_of_84_04(application: AppTest) -> None:
    run_checks(choose_product(load_bank_records(application), LoanProduct.MORTGAGE))

    application.button(key="check_valuer_report").click().run()

    assert not application.exception
    assert any("84/04" in message.value for message in application.error)


def test_audit_trail_verifies_the_hash_chain(application: AppTest) -> None:
    run_checks(load_bank_records(application))

    application.button(key="loan_verify_audit").click().run()

    assert application.success


def test_vehicle_case_labels_follow_the_language(application: AppTest) -> None:
    choose_product(application, LoanProduct.AUTO)

    application.radio(key=LANGUAGE_WIDGET_KEY).set_value(Language.ENGLISH).run()

    cases = application.radio(key=choice_widget_key("loan_vehicle_case", Language.ENGLISH))
    assert VEHICLE_DEMO_CASES[0].title[Language.ENGLISH] in cases.options


def test_vehicle_case_can_be_chosen_after_switching_language(application: AppTest) -> None:
    # The browser sends back the label of the chosen option; a label that changed with the
    # language once came back as the value: "KeyError: 'DEMO-CAR-001 · Toyota Prius: ...'".
    choose_product(application, LoanProduct.AUTO)
    application.radio(key=LANGUAGE_WIDGET_KEY).set_value(Language.ENGLISH).run()
    english_cases = application.radio(key=choice_widget_key("loan_vehicle_case", Language.ENGLISH))

    english_cases.set_value(VEHICLE_DEMO_CASES[1].application_id).run()

    assert not application.exception
    assert (
        application.session_state["collateral_vehicle_make"] == VEHICLE_DEMO_CASES[1].vehicle.make
    )
