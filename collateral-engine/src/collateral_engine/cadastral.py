"""Cadastral codes of the National Agency of Public Registry of Georgia (NAPR).

The structure is inferred from public registry extracts: four or five parcel segments, then a
building and a unit segment for a flat, for example 01.14.14.011.008.01.527 in Tbilisi. Verify it
against the NAPR rule on forming cadastral codes (Government Resolution No. 388) before production.
"""

import re
from dataclasses import dataclass
from typing import Annotated

from pydantic import AfterValidator

TBILISI_REGION_CODE = "01"

_CADASTRAL_CODE_PATTERN = re.compile(
    r"(?P<region>\d{2})\.(?P<second>\d{2})\.(?P<third>\d{2})\.(?P<parcel>\d{3})"
    r"(?:\.(?P<sub_parcel>\d{3}))?"
    r"(?:\.(?P<building>\d{2})\.(?P<unit>\d{3}))?"
)


class InvalidCadastralCodeError(ValueError):
    """The text is not a NAPR cadastral code."""


@dataclass(frozen=True)
class CadastralCodeParts:
    region: str
    parcel_code: str
    building_number: str | None
    unit_number: str | None

    @property
    def is_in_tbilisi(self) -> bool:
        return self.region == TBILISI_REGION_CODE

    @property
    def is_apartment_unit(self) -> bool:
        return self.unit_number is not None


def parse_cadastral_code(code: str) -> CadastralCodeParts:
    match = _CADASTRAL_CODE_PATTERN.fullmatch(code.strip())
    if match is None:
        raise InvalidCadastralCodeError(
            f"'{code}' is not a NAPR cadastral code such as 01.14.14.011.008.01.527"
        )
    parcel_segments = [match["region"], match["second"], match["third"], match["parcel"]]
    if match["sub_parcel"] is not None:
        parcel_segments.append(match["sub_parcel"])
    return CadastralCodeParts(
        region=match["region"],
        parcel_code=".".join(parcel_segments),
        building_number=match["building"],
        unit_number=match["unit"],
    )


def _require_tbilisi(code: str) -> str:
    if not parse_cadastral_code(code).is_in_tbilisi:
        raise ValueError("the model covers Tbilisi only (cadastral region 01)")
    return code.strip()


TbilisiCadastralCode = Annotated[str, AfterValidator(_require_tbilisi)]
