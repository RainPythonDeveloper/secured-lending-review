import numpy as np
import pytest

from ite import rules
from ite.synth import annuity


def chk(income, debt=0, payment=100, ccy="GEL", inc_ccy="GEL", as_of="2026-10-20", coll=None, amount=5000):
    return rules.check([income], [debt], [payment], [amount], [ccy], [inc_ccy], [0.18], [36],
                       None if coll is None else [coll], as_of)


@pytest.mark.parametrize("income,ccy,inc_ccy,limit", [
    (1000, "GEL", "GEL", 0.25), (1499, "GEL", "GEL", 0.25), (1500, "GEL", "GEL", 0.50),
    (1000, "USD", "GEL", 0.20), (3000, "USD", "GEL", 0.30), (3000, "USD", "USD", 0.50),
])
def test_pti_limits_2026(income, ccy, inc_ccy, limit):
    assert chk(income, ccy=ccy, inc_ccy=inc_ccy)["pti_limit"][0] == pytest.approx(limit)


def test_2027_thresholds_apply_by_date():
    assert chk(1800, as_of="2027-01-31")["pti_limit"][0] == 0.50
    assert chk(1800, as_of="2027-02-01")["pti_limit"][0] == 0.25
    assert chk(2400, as_of="2027-08-31")["pti_limit"][0] == 0.50
    assert chk(2400, as_of="2027-09-01")["pti_limit"][0] == 0.25
    assert chk(2400, as_of="2027-09-01")["rules_version"] == "2027-09"


def test_max_amount_is_exactly_compliant():
    c = chk(1200, debt=50)
    max_amt = c["max_amount"][0]
    pay = annuity(max_amt, 0.18, 36)
    assert (50 + pay) / 1200 == pytest.approx(0.25, rel=1e-6)


def test_debt_above_limit_gives_zero():
    assert chk(1000, debt=400)["max_amount"][0] == 0


def test_ltv_caps_amount():
    c = chk(10000, coll=10000, amount=9000)
    assert c["ltv_pass"][0] == False  # noqa: E712  (90% > 85%)
    assert c["max_amount"][0] <= 8500 + 1e-6


def test_fx_ltv_stricter():
    c = rules.check([10000], [0], [100], [7500], ["USD"], ["GEL"], [0.1], [60], [10000], "2026-10-20")
    assert c["ltv_limit"][0] == 0.70 and not c["ltv_pass"][0]


def test_no_rules_before_first_version():
    with pytest.raises(ValueError):
        rules.version_for("2010-01-01")
