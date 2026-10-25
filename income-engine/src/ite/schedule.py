"""Repayment schedules: standard annuity and a harvest-shaped (seasonal) schedule.

The seasonal schedule has the same present value as the annuity at the same rate, so the
lender earns the same; the borrower pays more in months when income actually arrives.
How NBG's PTI rule applies to non-equal schedules must be confirmed with NBG.
"""
from __future__ import annotations

import numpy as np


def annuity_schedule(principal: float, annual_rate: float, term: int) -> np.ndarray:
    r = annual_rate / 12
    return np.full(term, principal * r / (1 - (1 + r) ** -term))


def seasonal_schedule(principal: float, annual_rate: float, term: int, profile12: np.ndarray,
                      start_month: int, floor: float = 0.35, cap: float = 3.0) -> np.ndarray:
    """profile12: income by calendar month (Jan..Dec); start_month: 1..12 of first instalment."""
    r = annual_rate / 12
    prof = np.asarray(profile12, dtype=float)
    rel = prof / max(prof.mean(), 1e-9)
    w = np.clip(np.array([rel[(start_month - 1 + t) % 12] for t in range(term)]), floor, cap)
    disc = (1 + r) ** -np.arange(1, term + 1)
    k = principal / np.sum(w * disc)
    return k * w


def is_seasonal(season_top3: float, threshold: float = 0.45) -> bool:
    return bool(season_top3 >= threshold)
