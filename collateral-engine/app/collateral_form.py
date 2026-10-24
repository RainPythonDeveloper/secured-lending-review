"""The collateral in step 2 of the loan application: a demo case, or every field filled in by hand.

The hand-filled form starts from the chosen demo case, so the officer changes only what differs.
"""

from collections.abc import Callable
from datetime import date
from decimal import Decimal
from enum import StrEnum

import streamlit as st

import design
from collateral_engine.demo_cases import DEMO_CASES, DEMO_VALUATION_DATE, DemoCase
from collateral_engine.domain import (
    BuildingStatus,
    Condition,
    ConstructionStage,
    Currency,
    District,
    LicensedAppraisal,
    OffPlanDetails,
    PropertyKind,
    SubjectProperty,
)
from collateral_engine.i18n import (
    BUILDING_STATUS_NAMES,
    CONDITION_NAMES,
    CONSTRUCTION_STAGE_NAMES,
    FUEL_TYPE_NAMES,
    PROPERTY_KIND_NAMES,
    STEERING_SIDE_NAMES,
    Bilingual,
    Language,
)
from collateral_engine.lending.affordability import LoanProduct
from collateral_engine.lending.pipeline import RealEstateCollateral, VehicleCollateral
from collateral_engine.photos import PhotoUpload
from collateral_engine.reference import load_districts
from collateral_engine.vehicles.demo_cases import VEHICLE_DEMO_CASES, VehicleDemoCase
from collateral_engine.vehicles.domain import FuelType, SteeringSide, VehicleSubject
from language import choice
from report_view import label, money
from resources import get_engine, get_vehicle_engine

PHOTO_TYPES = ["jpg", "jpeg", "png", "webp"]
REAL_ESTATE_CASES = {case.application_id: case for case in DEMO_CASES}
VEHICLE_CASES = {case.application_id: case for case in VEHICLE_DEMO_CASES}
REAL_ESTATE_CASE_KEY = "loan_real_estate_case"
VEHICLE_CASE_KEY = "loan_vehicle_case"
MODE_KEY = "collateral_mode"
ESTATE_PREFIX = "collateral_estate_"
VEHICLE_PREFIX = "collateral_vehicle_"
PHOTO_KEYS = {
    LoanProduct.MORTGAGE: "loan_photos_real_estate",
    LoanProduct.AUTO: "loan_photos_vehicle",
}
# Shown in the land field while a flat is entered; a flat itself has no land area.
DEFAULT_LAND_AREA_M2 = 500.0
DISTRICT_NAMES: dict[District, Bilingual] = {
    district.code: {Language.GEORGIAN: district.name_ka, Language.ENGLISH: district.name_en}
    for district in load_districts().values()
}


class CollateralMode(StrEnum):
    DEMO = "demo"
    MANUAL = "manual"


def _named(names: dict, language: Language) -> Callable[[object], str]:
    return lambda option: names[option][language]


def _estate(name: str) -> str:
    return f"{ESTATE_PREFIX}{name}"


def _vehicle(name: str) -> str:
    return f"{VEHICLE_PREFIX}{name}"


# ------------------------------------------------------------------ state


def _real_estate_fields(case: DemoCase) -> dict[str, object]:
    subject, appraisal, off_plan = case.subject, case.appraisal, case.subject.off_plan
    return {
        "property_kind": subject.property_kind,
        "cadastral_code": subject.cadastral_code,
        "district": subject.district,
        "latitude": subject.latitude,
        "longitude": subject.longitude,
        "total_area_m2": float(subject.total_area_m2),
        "land_area_m2": float(subject.land_area_m2 or DEFAULT_LAND_AREA_M2),
        "rooms": subject.rooms,
        "floor": subject.floor,
        "building_floors": subject.building_floors,
        "building_status": subject.building_status,
        "declared_condition": subject.declared_condition,
        "developer_name": off_plan.developer_name if off_plan else "",
        "construction_stage": off_plan.construction_stage
        if off_plan
        else ConstructionStage.STRUCTURAL_FRAME,
        "expected_completion_date": off_plan.expected_completion_date
        if off_plan
        else DEMO_VALUATION_DATE,
        "purchase_agreement_registered": off_plan.purchase_agreement_registered
        if off_plan
        else False,
        "has_appraisal": appraisal is not None,
        "appraised_value": float(appraisal.market_value) if appraisal else 0.0,
        "appraisal_currency": appraisal.currency if appraisal else Currency.USD,
    }


def _vehicle_fields(case: VehicleDemoCase) -> dict[str, object]:
    vehicle = case.vehicle
    return {
        "vin": vehicle.vin,
        "plate_number": vehicle.plate_number or "",
        "make": vehicle.make,
        "model": vehicle.model,
        "production_year": vehicle.production_year,
        "mileage_km": vehicle.mileage_km,
        "engine_volume_cm3": vehicle.engine_volume_cm3,
        "fuel": vehicle.fuel,
        "steering": vehicle.steering,
        "is_customs_cleared": vehicle.is_customs_cleared,
        "has_accident_history": vehicle.has_accident_history,
    }


def _copy_real_estate_case() -> None:
    case = REAL_ESTATE_CASES[st.session_state[REAL_ESTATE_CASE_KEY]]
    for name, value in _real_estate_fields(case).items():
        st.session_state[_estate(name)] = value


def _copy_vehicle_case() -> None:
    case = VEHICLE_CASES[st.session_state[VEHICLE_CASE_KEY]]
    for name, value in _vehicle_fields(case).items():
        st.session_state[_vehicle(name)] = value


def _initialise() -> None:
    st.session_state.setdefault(MODE_KEY, CollateralMode.DEMO)
    if REAL_ESTATE_CASE_KEY not in st.session_state:
        st.session_state[REAL_ESTATE_CASE_KEY] = DEMO_CASES[0].application_id
        _copy_real_estate_case()
    if VEHICLE_CASE_KEY not in st.session_state:
        st.session_state[VEHICLE_CASE_KEY] = VEHICLE_DEMO_CASES[0].application_id
        _copy_vehicle_case()


def _keep_hidden_fields() -> None:
    # Streamlit drops the state of a widget that is not drawn in a run, so a hidden part of the
    # form (the demo mode, another product, the land field of a flat) would lose what was typed.
    for key in list(st.session_state):
        if key.startswith((ESTATE_PREFIX, VEHICLE_PREFIX)):
            st.session_state[key] = st.session_state[key]


def mode() -> CollateralMode:
    return st.session_state.get(MODE_KEY, CollateralMode.DEMO)


# ------------------------------------------------------------------ form


def render_collateral(product: LoanProduct, language: Language) -> None:
    _initialise()
    _keep_hidden_fields()
    if product is LoanProduct.CONSUMER:
        return
    is_real_estate = product is LoanProduct.MORTGAGE
    design.form_subhead(
        label("collateral_title", language),
        label(
            "collateral_title_real_estate" if is_real_estate else "collateral_title_vehicle",
            language,
        ),
    )
    selected = choice(
        st.radio,
        label("collateral_mode", language),
        list(CollateralMode),
        lambda option: label(f"collateral_mode_{option.value}", language),
        MODE_KEY,
        horizontal=True,
    )
    if is_real_estate:
        _render_real_estate(selected, language)
    else:
        _render_vehicle(selected, language)
    _render_photos(product, language)


def _render_real_estate(selected: CollateralMode, language: Language) -> None:
    if selected is CollateralMode.MANUAL:
        _render_real_estate_form(language)
        return
    case_column, summary_column = st.columns([2, 3], gap="large")
    with case_column:
        case_id = choice(
            st.radio,
            label("collateral_case", language),
            list(REAL_ESTATE_CASES),
            lambda option: REAL_ESTATE_CASES[option].title[language],
            REAL_ESTATE_CASE_KEY,
            on_change=_copy_real_estate_case,
        )
    with summary_column:
        _render_real_estate_summary(REAL_ESTATE_CASES[case_id], language)
        st.caption(label("collateral_demo_hint", language))


def _render_vehicle(selected: CollateralMode, language: Language) -> None:
    if selected is CollateralMode.MANUAL:
        _render_vehicle_form(language)
        return
    case_column, summary_column = st.columns([2, 3], gap="large")
    with case_column:
        case_id = choice(
            st.radio,
            label("collateral_case", language),
            list(VEHICLE_CASES),
            lambda option: VEHICLE_CASES[option].title[language],
            VEHICLE_CASE_KEY,
            on_change=_copy_vehicle_case,
        )
    with summary_column:
        _render_vehicle_summary(VEHICLE_CASES[case_id], language)
        st.caption(label("collateral_demo_hint", language))


def _render_real_estate_summary(case: DemoCase, language: Language) -> None:
    subject, appraisal = case.subject, case.appraisal
    is_house = subject.property_kind is PropertyKind.HOUSE
    area_note = (
        f"{label('land_area', language)}: {subject.land_area_m2:,.0f}"
        if is_house
        else f"{label('rooms', language)}: {subject.rooms}"
    )
    floors = (
        str(subject.building_floors) if is_house else f"{subject.floor} / {subject.building_floors}"
    )
    design.stat_cards(
        [
            design.Stat(
                PROPERTY_KIND_NAMES[subject.property_kind][language],
                DISTRICT_NAMES[subject.district][language],
                note=subject.cadastral_code,
            ),
            design.Stat(label("total_area", language), f"{subject.total_area_m2:,.1f}", area_note),
            design.Stat(label("floor_of_building", language), floors),
            design.Stat(
                label("building_status", language),
                BUILDING_STATUS_NAMES[subject.building_status][language],
            ),
            design.Stat(
                label("declared_condition", language),
                CONDITION_NAMES[subject.declared_condition][language],
            ),
            design.Stat(
                label("appraised_value", language),
                money(appraisal.market_value, appraisal.currency.value)
                if appraisal
                else label("no_appraisal", language),
            ),
        ],
        columns=3,
        is_compact=True,
    )


def _render_vehicle_summary(case: VehicleDemoCase, language: Language) -> None:
    vehicle = case.vehicle
    is_right_hand = vehicle.steering is SteeringSide.RIGHT
    design.stat_cards(
        [
            design.Stat(
                f"{vehicle.make} {vehicle.model}",
                str(vehicle.production_year),
                note=vehicle.vin,
            ),
            design.Stat(label("mileage", language), f"{vehicle.mileage_km:,}"),
            design.Stat(label("fuel", language), FUEL_TYPE_NAMES[vehicle.fuel][language]),
            design.Stat(
                label("steering", language),
                STEERING_SIDE_NAMES[vehicle.steering][language],
                tone=design.Tone.WARN if is_right_hand else design.Tone.PLAIN,
            ),
            design.Stat(
                label("customs_cleared", language),
                label("yes" if vehicle.is_customs_cleared else "no", language),
                tone=design.Tone.PLAIN if vehicle.is_customs_cleared else design.Tone.BAD,
            ),
            design.Stat(
                label("accident_history", language),
                label("yes" if vehicle.has_accident_history else "no", language),
                tone=design.Tone.WARN if vehicle.has_accident_history else design.Tone.PLAIN,
            ),
        ],
        columns=3,
        is_compact=True,
    )


def _render_real_estate_form(language: Language) -> None:
    st.caption(label("collateral_manual_hint", language))
    property_kind = choice(
        st.radio,
        label("property_kind", language),
        list(PropertyKind),
        _named(PROPERTY_KIND_NAMES, language),
        _estate("property_kind"),
        horizontal=True,
        help=label("house_hint", language),
    )
    code_column, district_column = st.columns([3, 2])
    code_column.text_input(label("cadastral_code", language), key=_estate("cadastral_code"))
    with district_column:
        choice(
            st.selectbox,
            label("district", language),
            list(District),
            _named(DISTRICT_NAMES, language),
            _estate("district"),
        )
    latitude_column, longitude_column = st.columns(2)
    latitude_column.number_input(
        label("latitude", language), key=_estate("latitude"), format="%.5f", step=0.001
    )
    longitude_column.number_input(
        label("longitude", language), key=_estate("longitude"), format="%.5f", step=0.001
    )
    _render_size_fields(property_kind, language)
    status = _render_building_fields(language)
    if status is BuildingStatus.UNDER_CONSTRUCTION:
        _render_off_plan_fields(language)
    _render_appraisal_fields(language)


def _render_size_fields(property_kind: PropertyKind, language: Language) -> None:
    area_column, rooms_column, floor_column, floors_column = st.columns(4)
    area_column.number_input(
        label("total_area", language),
        key=_estate("total_area_m2"),
        min_value=15.0,
        max_value=1000.0,
        step=0.5,
    )
    rooms_column.number_input(
        label("rooms", language), key=_estate("rooms"), min_value=1, max_value=12, step=1
    )
    if property_kind is PropertyKind.HOUSE:
        floor_column.number_input(
            label("land_area", language),
            key=_estate("land_area_m2"),
            min_value=20.0,
            max_value=100000.0,
            step=10.0,
        )
    else:
        floor_column.number_input(
            label("floor", language), key=_estate("floor"), min_value=1, max_value=70, step=1
        )
    floors_column.number_input(
        label("building_floors", language),
        key=_estate("building_floors"),
        min_value=1,
        max_value=70,
        step=1,
    )


def _render_building_fields(language: Language) -> BuildingStatus:
    status_column, condition_column = st.columns(2)
    with status_column:
        status = choice(
            st.selectbox,
            label("building_status", language),
            list(BuildingStatus),
            _named(BUILDING_STATUS_NAMES, language),
            _estate("building_status"),
        )
    with condition_column:
        choice(
            st.selectbox,
            label("declared_condition", language),
            list(Condition),
            _named(CONDITION_NAMES, language),
            _estate("declared_condition"),
        )
    return status


def _render_off_plan_fields(language: Language) -> None:
    design.form_subhead(label("off_plan_section", language))
    developer_column, stage_column, completion_column = st.columns(3)
    developer_column.text_input(label("developer_name", language), key=_estate("developer_name"))
    with stage_column:
        choice(
            st.selectbox,
            label("construction_stage", language),
            list(ConstructionStage),
            _named(CONSTRUCTION_STAGE_NAMES, language),
            _estate("construction_stage"),
        )
    completion_column.date_input(
        label("expected_completion_date", language), key=_estate("expected_completion_date")
    )
    st.checkbox(
        label("agreement_registered", language), key=_estate("purchase_agreement_registered")
    )


def _render_appraisal_fields(language: Language) -> None:
    has_appraisal = st.toggle(label("has_appraisal", language), key=_estate("has_appraisal"))
    if not has_appraisal:
        return
    value_column, currency_column = st.columns([3, 2])
    value_column.number_input(
        label("appraised_value", language),
        key=_estate("appraised_value"),
        min_value=0.0,
        step=1000.0,
    )
    currency_column.radio(
        label("appraisal_currency", language),
        list(Currency),
        key=_estate("appraisal_currency"),
        horizontal=True,
    )


def _render_vehicle_form(language: Language) -> None:
    st.caption(label("collateral_manual_hint", language))
    vin_column, plate_column = st.columns([2, 1])
    vin_column.text_input(label("vin", language), key=_vehicle("vin"))
    plate_column.text_input(label("plate_number", language), key=_vehicle("plate_number"))
    make_column, model_column, year_column = st.columns(3)
    make_column.text_input(label("make", language), key=_vehicle("make"))
    model_column.text_input(label("model", language), key=_vehicle("model"))
    year_column.number_input(
        label("production_year", language), key=_vehicle("production_year"), min_value=1990
    )
    mileage_column, engine_column, fuel_column = st.columns(3)
    mileage_column.number_input(
        label("mileage", language), key=_vehicle("mileage_km"), min_value=0, step=1000
    )
    engine_column.number_input(
        label("engine_volume", language), key=_vehicle("engine_volume_cm3"), min_value=0, step=100
    )
    with fuel_column:
        choice(
            st.selectbox,
            label("fuel", language),
            list(FuelType),
            _named(FUEL_TYPE_NAMES, language),
            _vehicle("fuel"),
        )
    steering_column, customs_column, accident_column = st.columns(3)
    with steering_column:
        choice(
            st.radio,
            label("steering", language),
            list(SteeringSide),
            _named(STEERING_SIDE_NAMES, language),
            _vehicle("steering"),
            horizontal=True,
        )
    customs_column.checkbox(label("customs_cleared", language), key=_vehicle("is_customs_cleared"))
    accident_column.checkbox(
        label("accident_history", language), key=_vehicle("has_accident_history")
    )


def _render_photos(product: LoanProduct, language: Language) -> None:
    if product is LoanProduct.MORTGAGE:
        text = label("photos", language, count=get_engine().config.condition_rules.min_photos)
    else:
        count = get_vehicle_engine().config.policy.evidence.min_photos
        text = label("vehicle_photos", language, count=count)
    st.file_uploader(
        text,
        type=PHOTO_TYPES,
        accept_multiple_files=True,
        key=PHOTO_KEYS[product],
        help=label("photos_optional", language),
    )


# ------------------------------------------------------------------ application


def photo_uploads(product: LoanProduct) -> list[PhotoUpload]:
    if product is LoanProduct.CONSUMER:
        return []
    return [
        PhotoUpload(upload.name, upload.getvalue())
        for upload in st.session_state.get(PHOTO_KEYS[product]) or []
    ]


def real_estate_collateral(application_date: date) -> RealEstateCollateral:
    """Raises ValidationError when the entered property is not valid."""
    if mode() is CollateralMode.DEMO:
        case = REAL_ESTATE_CASES[st.session_state[REAL_ESTATE_CASE_KEY]]
        return RealEstateCollateral(subject=case.subject, appraisal=case.appraisal)
    return RealEstateCollateral(
        subject=_entered_subject(), appraisal=_entered_appraisal(application_date)
    )


def vehicle_collateral() -> VehicleCollateral:
    """Raises ValidationError when the entered vehicle is not valid."""
    if mode() is CollateralMode.DEMO:
        return VehicleCollateral(vehicle=VEHICLE_CASES[st.session_state[VEHICLE_CASE_KEY]].vehicle)
    field = _vehicle_field
    return VehicleCollateral(
        vehicle=VehicleSubject(
            vin=str(field("vin")).strip().upper(),
            plate_number=str(field("plate_number")).strip().upper() or None,
            make=str(field("make")).strip(),
            model=str(field("model")).strip(),
            production_year=field("production_year"),
            mileage_km=field("mileage_km"),
            engine_volume_cm3=field("engine_volume_cm3"),
            fuel=field("fuel"),
            steering=field("steering"),
            is_customs_cleared=field("is_customs_cleared"),
            has_accident_history=field("has_accident_history"),
        )
    )


def _estate_field(name: str) -> object:
    return st.session_state[_estate(name)]


def _vehicle_field(name: str) -> object:
    return st.session_state[_vehicle(name)]


def _entered_subject() -> SubjectProperty:
    field = _estate_field
    is_house = field("property_kind") is PropertyKind.HOUSE
    return SubjectProperty(
        cadastral_code=str(field("cadastral_code")).strip(),
        property_kind=field("property_kind"),
        land_area_m2=Decimal(str(field("land_area_m2"))) if is_house else None,
        district=field("district"),
        latitude=field("latitude"),
        longitude=field("longitude"),
        total_area_m2=Decimal(str(field("total_area_m2"))),
        rooms=field("rooms"),
        # A house is entered at ground level; its storeys go into building_floors.
        floor=1 if is_house else field("floor"),
        building_floors=field("building_floors"),
        building_status=field("building_status"),
        declared_condition=field("declared_condition"),
        off_plan=_entered_off_plan(),
    )


def _entered_off_plan() -> OffPlanDetails | None:
    field = _estate_field
    if field("building_status") is not BuildingStatus.UNDER_CONSTRUCTION:
        return None
    return OffPlanDetails(
        developer_name=str(field("developer_name")).strip(),
        construction_stage=field("construction_stage"),
        expected_completion_date=field("expected_completion_date"),
        purchase_agreement_registered=field("purchase_agreement_registered"),
    )


def _entered_appraisal(application_date: date) -> LicensedAppraisal | None:
    if not _estate_field("has_appraisal"):
        return None
    return LicensedAppraisal(
        market_value=Decimal(str(_estate_field("appraised_value"))),
        currency=_estate_field("appraisal_currency"),
        appraisal_date=application_date,
    )
