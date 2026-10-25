"""Client of our Open Banking gateway (server/): the customer's consent, then accounts and history.

The gateway runs the Berlin Group consent journey at the TBC sandbox and serves the NBG hackathon
dataset for the customer named in PSU-ID. Field names follow the TBC specification. The gateway
retries the sandbox's injected failures itself; this client sets a timeout on every call and sends
a fresh X-Request-ID with each one.
"""

import logging
import uuid
from datetime import date, timedelta
from decimal import Decimal

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from collateral_engine.lending.customer import (
    AccountSummary,
    Customer,
    CustomerFile,
    DataSource,
    StatementTransaction,
)

logger = logging.getLogger(__name__)

CONSENT_VALIDITY_DAYS = 30
CONSENT_FREQUENCY_PER_DAY = 4
VALID_CONSENT_STATUS = "valid"
# The gateway answers on localhost; any caller address will do for the PSU-IP-Address header.
PSU_IP_ADDRESS = "127.0.0.1"


class OpenBankingError(Exception):
    """The gateway or the bank could not serve the request; the caller may fall back."""


class _Gateway(BaseModel):
    model_config = ConfigDict(frozen=True, extra="ignore")


class _Href(_Gateway):
    href: str


class _ConsentLinks(_Gateway):
    scaRedirect: _Href  # noqa: N815 - Berlin Group field name


class _CreatedConsent(_Gateway):
    consentId: str  # noqa: N815
    consentStatus: str  # noqa: N815
    psuMessage: str = ""  # noqa: N815
    links: _ConsentLinks = Field(alias="_links")


class _ConsentStatus(_Gateway):
    consentStatus: str  # noqa: N815


class _Amount(_Gateway):
    amount: str
    currency: str


class _Balance(_Gateway):
    balanceAmount: _Amount  # noqa: N815


class _Account(_Gateway):
    resourceId: str  # noqa: N815
    currency: str
    product: str = ""
    balances: list[_Balance] = []


class _AccountList(_Gateway):
    accounts: list[_Account]


class _Transaction(_Gateway):
    transactionId: str  # noqa: N815
    bookingDate: date  # noqa: N815
    transactionAmount: _Amount  # noqa: N815
    creditorName: str = ""  # noqa: N815
    debtorName: str = ""  # noqa: N815
    remittanceInformationUnstructured: str = ""  # noqa: N815
    proprietaryBankTransactionCode: str = ""  # noqa: N815


class _Report(_Gateway):
    booked: list[_Transaction] = []


class _TransactionList(_Gateway):
    transactions: _Report


class ConsentStart(BaseModel):
    model_config = ConfigDict(frozen=True)

    consent_id: str
    # The bank page where the customer approves access; the gateway's callback completes it.
    authorisation_url: str
    data_source: str
    message: str


class OpenBankingClient:
    def __init__(self, http_client: httpx.Client, base_url: str, timeout_s: float) -> None:
        self._http_client = http_client
        self._base_url = base_url.rstrip("/")
        self._timeout_s = timeout_s

    def start_consent(self, customer_id: str, today: date) -> ConsentStart:
        body = {
            "access": {"accounts": [], "balances": [], "transactions": []},
            "recurringIndicator": True,
            "validUntil": (today + timedelta(days=CONSENT_VALIDITY_DAYS)).isoformat(),
            "frequencyPerDay": CONSENT_FREQUENCY_PER_DAY,
            "combinedServiceIndicator": False,
        }
        response = self._send("POST", "/v1/consents", json=body, headers={"PSU-ID": customer_id})
        consent = _validated(_CreatedConsent, response)
        return ConsentStart(
            consent_id=consent.consentId,
            authorisation_url=consent.links.scaRedirect.href,
            data_source=response.headers.get("X-Data-Source", ""),
            message=consent.psuMessage,
        )

    def is_consent_valid(self, consent_id: str) -> bool:
        response = self._send("GET", f"/v1/consents/{consent_id}/status")
        status = _validated(_ConsentStatus, response)
        return status.consentStatus == VALID_CONSENT_STATUS

    def customer_file(
        self, consent_id: str, customer: Customer, period_start: date, period_end: date
    ) -> CustomerFile:
        """Accounts and booked transactions in [period_start, period_end) under the consent."""
        consent = {"Consent-ID": consent_id}
        response = self._send(
            "GET", "/v1/accounts", params={"withBalance": "true"}, headers=consent
        )
        accounts = _validated(_AccountList, response).accounts
        transactions = [
            transaction
            for account in accounts
            for transaction in self._transactions(consent, account, period_start, period_end)
        ]
        return CustomerFile(
            customer=customer,
            accounts=[_account_summary(account) for account in accounts],
            transactions=transactions,
            source=DataSource.OPEN_BANKING,
            period_start=period_start,
            period_end=period_end,
            consent_id=consent_id,
        )

    def _transactions(
        self, consent: dict[str, str], account: _Account, period_start: date, period_end: date
    ) -> list[StatementTransaction]:
        params = {
            "dateFrom": period_start.isoformat(),
            "dateTo": (period_end - timedelta(days=1)).isoformat(),
            "bookingStatus": "booked",
        }
        response = self._send(
            "GET", f"/v1/accounts/{account.resourceId}/transactions", params=params, headers=consent
        )
        report = _validated(_TransactionList, response)
        return [_statement_transaction(account, item) for item in report.transactions.booked]

    def _send(
        self,
        method: str,
        path: str,
        *,
        json: dict | None = None,
        params: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        request_id = str(uuid.uuid4())
        all_headers = {
            "X-Request-ID": request_id,
            "PSU-IP-Address": PSU_IP_ADDRESS,
            "Accept": "application/json",
            **(headers or {}),
        }
        logger.info("Open Banking %s %s, X-Request-ID %s", method, path, request_id)
        try:
            response = self._http_client.request(
                method,
                f"{self._base_url}{path}",
                json=json,
                params=params,
                headers=all_headers,
                timeout=self._timeout_s,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as error:
            raise OpenBankingError(
                f"{method} {path} answered {error.response.status_code}: {_detail(error)}"
            ) from error
        except httpx.HTTPError as error:
            raise OpenBankingError(f"{method} {path} failed: {type(error).__name__}") from error
        return response


def _validated[Model: BaseModel](model: type[Model], response: httpx.Response) -> Model:
    try:
        return model.model_validate(response.json())
    except (ValidationError, ValueError) as error:
        raise OpenBankingError(f"the gateway answered an unexpected body: {error}") from error


def _detail(error: httpx.HTTPStatusError) -> str:
    try:
        return str(error.response.json().get("detail", ""))
    except ValueError:
        return ""


def _account_summary(account: _Account) -> AccountSummary:
    balance = account.balances[0].balanceAmount.amount if account.balances else "0"
    return AccountSummary(
        account_id=account.resourceId,
        account_type=account.product or "current",
        currency=account.currency,
        closing_balance=Decimal(balance),
    )


def _statement_transaction(account: _Account, item: _Transaction) -> StatementTransaction:
    return StatementTransaction(
        transaction_id=item.transactionId,
        account_id=account.resourceId,
        booking_date=item.bookingDate,
        amount=Decimal(item.transactionAmount.amount),
        currency=item.transactionAmount.currency,
        category=item.proprietaryBankTransactionCode,
        counterparty=item.debtorName or item.creditorName,
        description=item.remittanceInformationUnstructured,
    )
