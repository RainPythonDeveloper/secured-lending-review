"""Reading a CSV file whose rows must each satisfy a pydantic model."""

import csv
from collections.abc import Iterable
from pathlib import Path

from pydantic import BaseModel, ValidationError

MAX_REPORTED_ROW_ERRORS = 5


class DataContractError(ValueError):
    """The file breaks its data contract: wrong header or invalid rows."""


def read_validated_rows[Row: BaseModel](path: Path, row_model: type[Row]) -> list[Row]:
    """Rejects the whole file and names the line and field of the first invalid rows."""
    columns = tuple(row_model.model_fields)
    with path.open(newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        if reader.fieldnames is None or tuple(reader.fieldnames) != columns:
            raise DataContractError(f"{path}: the header must be {','.join(columns)}")
        rows, row_errors = _parse_rows(reader, row_model)
    if row_errors:
        shown = "; ".join(row_errors[:MAX_REPORTED_ROW_ERRORS])
        raise DataContractError(f"{path}: {len(row_errors)} rows break the data contract: {shown}")
    return rows


def _parse_rows[Row: BaseModel](
    reader: csv.DictReader, row_model: type[Row]
) -> tuple[list[Row], list[str]]:
    rows: list[Row] = []
    row_errors: list[str] = []
    for line_number, row in enumerate(reader, start=2):
        try:
            rows.append(row_model.model_validate(row))
        except ValidationError as error:
            first = error.errors()[0]
            location = ".".join(str(part) for part in first["loc"])
            row_errors.append(f"line {line_number}: {location}: {first['msg']}")
    return rows, row_errors


def write_rows(rows: Iterable[BaseModel], row_model: type[BaseModel], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=tuple(row_model.model_fields))
        writer.writeheader()
        for row in rows:
            writer.writerow(row.model_dump(mode="json"))
