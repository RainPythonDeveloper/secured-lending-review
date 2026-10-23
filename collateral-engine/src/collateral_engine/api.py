"""REST API of the collateral engine; OpenAPI at /docs.

Errors are application/problem+json with type, title, status, code and detail, as in the Open
Banking gateway of this repository.

    uvicorn collateral_engine.api:create_app_from_environment --factory --port 8100
"""

import logging
from datetime import date
from http import HTTPStatus
from typing import Annotated

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, ValidationError

from collateral_engine import MODEL_VERSION
from collateral_engine.audit import (
    OfficerDecision,
    OfficerDecisionKind,
    ReasonRequiredError,
    UnknownValuationError,
    record_officer_decision,
)
from collateral_engine.bootstrap import build_engine, build_nbg_rates_client
from collateral_engine.domain import Currency, ExchangeRate, ValuationRequest
from collateral_engine.engine import CollateralEngine, TooManyPhotosError
from collateral_engine.nbg_rates import NbgRatesClient, OfficialRateUnavailableError
from collateral_engine.nbg_rules import NoRuleInForceError, rule_version_in_force
from collateral_engine.photos import PhotoUpload
from collateral_engine.reference import DistrictReference, load_districts
from collateral_engine.report import ValuationReport
from collateral_engine.report_check import ReportFinding, ValuerReport, check_valuer_report
from collateral_engine.settings import load_settings

logger = logging.getLogger(__name__)

PROBLEM_JSON = "application/problem+json"


class ProblemDetails(BaseModel):
    type: str = "about:blank"
    title: str
    status: int
    code: str
    detail: str


class HealthStatus(BaseModel):
    status: str
    model_version: str
    comparable_sales: int


class DecisionBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    officer_id: str
    decision: OfficerDecisionKind
    reason: str = ""


class DecisionRecorded(BaseModel):
    record_hash: str


class ReportCheckResult(BaseModel):
    nbg_rules_version: str
    findings: list[ReportFinding]


class AuditVerification(BaseModel):
    is_intact: bool
    records_checked: int


class ApiError(Exception):
    def __init__(self, status: HTTPStatus, code: str, detail: str) -> None:
        super().__init__(detail)
        self.status = status
        self.code = code
        self.detail = detail


def problem_response(status: HTTPStatus, code: str, detail: str) -> JSONResponse:
    problem = ProblemDetails(title=status.phrase, status=status.value, code=code, detail=detail)
    return JSONResponse(problem.model_dump(), status_code=status.value, media_type=PROBLEM_JSON)


def create_app(engine: CollateralEngine, rates_client: NbgRatesClient) -> FastAPI:
    app = FastAPI(
        title="Collateral second opinion",
        version=MODEL_VERSION,
        description="Valuation of Tbilisi flats offered as collateral, condition check from "
        "photos and the NBG LTV check. Demo build on synthetic comparable sales.",
    )
    _register_error_handlers(app)
    _register_routes(app, engine, rates_client)
    return app


def create_app_from_environment() -> FastAPI:
    settings = load_settings()
    return create_app(build_engine(settings), build_nbg_rates_client(settings))


def _register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def handle_api_error(_: Request, error: ApiError) -> JSONResponse:
        return problem_response(error.status, error.code, error.detail)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(_: Request, error: RequestValidationError) -> JSONResponse:
        return problem_response(
            HTTPStatus.BAD_REQUEST, "FORMAT_ERROR", _first_error(error.errors())
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(_: Request, error: Exception) -> JSONResponse:
        logger.exception("Unhandled error: %s", type(error).__name__)
        return problem_response(
            HTTPStatus.INTERNAL_SERVER_ERROR, "INTERNAL_ERROR", "unexpected error; see server log"
        )


def _first_error(errors: list) -> str:
    if not errors:
        return "invalid request"
    first = errors[0]
    location = ".".join(str(part) for part in first.get("loc", ()))
    return f"{location}: {first.get('msg', 'invalid value')}"


def _register_routes(app: FastAPI, engine: CollateralEngine, rates_client: NbgRatesClient) -> None:
    @app.get("/health")
    def health() -> HealthStatus:
        return HealthStatus(
            status="ok", model_version=MODEL_VERSION, comparable_sales=len(engine.market)
        )

    @app.get("/v1/reference/districts")
    def districts() -> list[DistrictReference]:
        return list(load_districts().values())

    @app.get("/v1/exchange-rates/usd")
    def usd_rate(rate_date: date) -> ExchangeRate:
        try:
            return rates_client.fetch_rate(Currency.USD, rate_date)
        except OfficialRateUnavailableError as error:
            raise ApiError(HTTPStatus.BAD_GATEWAY, "RATE_UNAVAILABLE", str(error)) from error

    @app.post("/v1/valuations", status_code=HTTPStatus.CREATED)
    def create_valuation(
        request: Annotated[str, Form(description="ValuationRequest as JSON")],
        photos: Annotated[list[UploadFile], File()] = [],  # noqa: B006 - FastAPI form default
    ) -> ValuationReport:
        valuation_request = _parse_valuation_request(request)
        uploads = [_read_upload(photo, engine.config.policy.photos.max_bytes) for photo in photos]
        try:
            return engine.assess(valuation_request, uploads)
        except TooManyPhotosError as error:
            raise ApiError(HTTPStatus.BAD_REQUEST, "TOO_MANY_PHOTOS", str(error)) from error
        except NoRuleInForceError as error:
            raise ApiError(
                HTTPStatus.UNPROCESSABLE_ENTITY, "NO_RULE_IN_FORCE", str(error)
            ) from error

    @app.post("/v1/valuations/{valuation_id}/decision", status_code=HTTPStatus.CREATED)
    def record_decision(valuation_id: str, body: DecisionBody) -> DecisionRecorded:
        decision = OfficerDecision(valuation_id=valuation_id, **body.model_dump())
        try:
            return DecisionRecorded(record_hash=record_officer_decision(engine.audit_log, decision))
        except UnknownValuationError as error:
            raise ApiError(HTTPStatus.NOT_FOUND, "RESOURCE_UNKNOWN", str(error)) from error
        except ReasonRequiredError as error:
            raise ApiError(
                HTTPStatus.UNPROCESSABLE_ENTITY, "REASON_REQUIRED", str(error)
            ) from error

    @app.post("/v1/valuer-reports/check")
    def check_report(report: ValuerReport) -> ReportCheckResult:
        try:
            version = rule_version_in_force(engine.config.nbg_rules, report.valuation_date)
        except NoRuleInForceError as error:
            raise ApiError(
                HTTPStatus.UNPROCESSABLE_ENTITY, "NO_RULE_IN_FORCE", str(error)
            ) from error
        findings = check_valuer_report(report, version.valuation)
        return ReportCheckResult(nbg_rules_version=version.id, findings=findings)

    @app.get("/v1/audit/verify")
    def verify_audit() -> AuditVerification:
        is_intact, records_checked = engine.audit_log.verify()
        return AuditVerification(is_intact=is_intact, records_checked=records_checked)


def _parse_valuation_request(raw_request: str) -> ValuationRequest:
    try:
        return ValuationRequest.model_validate_json(raw_request)
    except ValidationError as error:
        raise ApiError(
            HTTPStatus.BAD_REQUEST, "FORMAT_ERROR", _first_error(error.errors())
        ) from error


def _read_upload(photo: UploadFile, max_bytes: int) -> PhotoUpload:
    # One byte over the limit is enough for the photo check to reject the file.
    return PhotoUpload(filename=photo.filename or "photo", content=photo.file.read(max_bytes + 1))
