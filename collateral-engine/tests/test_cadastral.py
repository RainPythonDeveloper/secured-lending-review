import pytest
from pydantic import TypeAdapter, ValidationError

from collateral_engine.cadastral import (
    InvalidCadastralCodeError,
    TbilisiApartmentCadastralCode,
    parse_cadastral_code,
)

TBILISI_APARTMENT_CODE = TypeAdapter(TbilisiApartmentCadastralCode)


def test_parse_splits_flat_code_into_parcel_building_and_unit() -> None:
    parts = parse_cadastral_code("01.14.14.011.008.01.527")

    assert (parts.region, parts.parcel_code, parts.building_number, parts.unit_number) == (
        "01",
        "01.14.14.011.008",
        "01",
        "527",
    )


@pytest.mark.parametrize(
    ("code", "is_apartment_unit"),
    [
        ("01.14.14.011.008.01.527", True),
        ("01.14.14.011.01.527", True),
        ("01.15.02.058.021", False),
        ("02.05.11.555", False),
    ],
)
def test_parse_accepts_registry_code_shapes(code: str, is_apartment_unit: bool) -> None:
    assert parse_cadastral_code(code).is_apartment_unit is is_apartment_unit


@pytest.mark.parametrize(
    "code",
    ["", "01-14-14-011-008", "1.14.14.011.008", "01.14.14.11.008", "01.14.14.011.008.01", "abc"],
)
def test_parse_rejects_text_that_is_not_a_registry_code(code: str) -> None:
    with pytest.raises(InvalidCadastralCodeError):
        parse_cadastral_code(code)


def test_tbilisi_apartment_code_accepts_flat_in_tbilisi() -> None:
    assert TBILISI_APARTMENT_CODE.validate_python(" 01.14.14.011.008.01.527 ") == (
        "01.14.14.011.008.01.527"
    )


def test_tbilisi_apartment_code_rejects_other_region() -> None:
    with pytest.raises(ValidationError, match="Tbilisi only"):
        TBILISI_APARTMENT_CODE.validate_python("02.05.11.555.001.01.501")


def test_tbilisi_apartment_code_rejects_land_parcel() -> None:
    with pytest.raises(ValidationError, match="flats only"):
        TBILISI_APARTMENT_CODE.validate_python("01.15.02.058.021")
