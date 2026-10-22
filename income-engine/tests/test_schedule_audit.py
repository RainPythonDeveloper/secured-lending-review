import numpy as np
import pytest

from ite.audit import AuditLog
from ite.schedule import annuity_schedule, seasonal_schedule


def pv(p, rate):
    return float(np.sum(p * (1 + rate / 12) ** -np.arange(1, len(p) + 1)))


def test_seasonal_same_present_value_as_annuity():
    prof = np.array([300] * 7 + [3600, 3300, 2900] + [300] * 2, float)
    for term in (12, 24, 36):
        s = seasonal_schedule(10000, 0.18, term, prof, start_month=8)
        a = annuity_schedule(10000, 0.18, term)
        assert pv(s, 0.18) == pytest.approx(10000, rel=1e-9)
        assert pv(a, 0.18) == pytest.approx(10000, rel=1e-9)
        assert s[:3].mean() > a[0] > s[3:12].mean()      # pays more in harvest, less off-season


def test_flat_income_gives_annuity():
    s = seasonal_schedule(5000, 0.2, 24, np.full(12, 1000.0), 1)
    assert np.allclose(s, annuity_schedule(5000, 0.2, 24))


def test_audit_chain_detects_tampering(tmp_path):
    log = AuditLog(tmp_path / "a.db")
    for i in range(5):
        log.append({"borrower_id": i, "decision": "APPROVE"})
    assert log.verify() == (True, 5)
    import sqlite3
    with sqlite3.connect(log.path) as c:
        c.execute("UPDATE decisions SET payload = replace(payload, 'APPROVE', 'REJECT') WHERE seq = 3")
    assert log.verify()[0] is False
