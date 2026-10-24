"""Identity and watchlist checks: sanctions and PEP lists, and the NAPR Debtors Registry.

Both lists are synthetic stand-ins (config/screening_lists.yaml). Identity is the bank's customer
record or the applicant's stated identity; nothing is read from a face or a voice.
"""

from pydantic import BaseModel, ConfigDict

from collateral_engine.lending.customer import Customer
from collateral_engine.lending.policy import DebtorRecord, SanctionsEntry, ScreeningLists


class ScreeningResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    lists_version: str
    sanctions_matches: list[SanctionsEntry]
    debtor_records: list[DebtorRecord]


def _normalised(name: str) -> str:
    return " ".join(name.casefold().split())


def screen_customer(customer: Customer, lists: ScreeningLists) -> ScreeningResult:
    name = _normalised(customer.full_name)
    return ScreeningResult(
        lists_version=lists.version,
        sanctions_matches=[
            entry for entry in lists.sanctions_and_pep if _normalised(entry.full_name) == name
        ],
        debtor_records=[
            record
            for record in lists.debtors_registry
            if record.customer_id == customer.customer_id
        ],
    )
