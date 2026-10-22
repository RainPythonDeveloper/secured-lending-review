"""Synthetic Georgian retail-lending data generator (100% SYNTHETIC DATA).

v2 design (fixes the "model rediscovers the formula" problem of v1):
  * Default depends partly on things the model can NEVER see: a latent financial
    fragility trait and post-application shocks (job loss, bad harvest, illness).
  * Observable behaviour (savings, late bills, betting, bureau score) is only a noisy
    proxy of that fragility, so realistic AUCs come out, not inflated ones.
  * Two application cohorts (Jul-2025 and Jul-2026) with mild drift give an honest
    out-of-time test.
  * Real-world mess: income at other banks, own-account transfers, one-off inflows,
    mixed Georgian/Latin descriptions, and "round-trip" fraud that fakes income.

Every column starting with TRUE_ / is_round_trip / category_true is hidden ground
truth used only for evaluation and for training the transaction categoriser.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

USD_GEL = 2.70          # replace with NBG monthly USD/GEL series for final calibration
OBS_MONTHS = 18         # months of transaction history before the application

# name: share, median monthly income (GEL), log-sigma, monthly vol, harvest months,
#       remittance share, declared-income bias, region, P(thin file), P(post-app shock),
#       share of income received in CASH (never visible in bank data)
ARCHETYPES = {
    "salaried_tbilisi": dict(share=.32, median=2100, sigma=.35, vol=.05, harvest=(),
                             remit=.00, bias=.00, region="Tbilisi", thin=.15, shock=.05, cash=.02),
    "farmer_kakheti":   dict(share=.20, median=1350, sigma=.45, vol=.12, harvest=(8, 9, 10),
                             remit=.10, bias=-.25, region="Kakheti", thin=.55, shock=.09, cash=.35),
    "self_employed":    dict(share=.20, median=1750, sigma=.50, vol=.30, harvest=(),
                             remit=.05, bias=.10, region="Imereti", thin=.30, shock=.07, cash=.30),
    "remittance_hh":    dict(share=.16, median=1150, sigma=.40, vol=.18, harvest=(),
                             remit=.80, bias=-.10, region="Samegrelo", thin=.40, shock=.06, cash=.15),
    "young_first_loan": dict(share=.12, median=1250, sigma=.30, vol=.10, harvest=(),
                             remit=.00, bias=.05, region="Tbilisi", thin=.80, shock=.06, cash=.10),
}

DESC = {
    "salary": ["ხელფასი", "ხელფასის ჩარიცხვა", "Salary", "ხელფ. ჩარიცხვა", "SALARY PAYMENT"],
    "harvest": ["მოსავლის რეალიზაცია", "ყურძნის ჩაბარება", "გადახდა ღვინის ქარხნიდან", "Grape delivery payment"],
    "p2p_in": ["გადმორიცხვა", "Transfer from client", "მომსახურების საფასური", "ჩარიცხვა"],
    "remittance": ["ფულადი გზავნილი", "Money transfer received", "გზავნილი საზღვარგარეთიდან", "Remittance"],
    "own_transfer": ["საკუთარ ანგარიშზე გადარიცხვა", "Own account transfer", "გადარიცხვა საკუთარ ანგარიშებს შორის"],
    "one_off_in": ["ავტომობილის გაყიდვა", "საჩუქარი", "Gift", "ერთჯერადი ჩარიცხვა"],
    "savings": ["ანაბარზე გადატანა", "Savings deposit", "შემნახველი ანაბარი"],
    "card_spend": ["სუპერმარკეტი", "მარკეტი", "POS purchase", "ბარათით გადახდა", "აფთიაქი"],
    "utilities": ["კომუნალური გადასახადი", "ელექტროენერგია", "ბუნებრივი აირი", "Water utility", "Utility payment"],
    "loan_repayment": ["სესხის დაფარვა", "Loan repayment", "კრედიტის შენატანი"],
    "betting": ["ტოტალიზატორი", "ონლაინ კაზინო", "Betting", "სპორტული ფსონი"],
    "p2p_out": ["გადარიცხვა", "Transfer to", "P2P გადარიცხვა"],
}
INFLOW_CATS = ["salary", "harvest", "p2p_in", "remittance"]
# Real statements are messy: many lines carry only a generic text, so the categoriser must
# also use amount, timing, currency, recurrence and whether the counterparty is an own account.
GENERIC_IN = ["ჩარიცხვა", "Transfer", "გადმორიცხვა", "Incoming transfer"]
GENERIC_OUT = ["გადარიცხვა", "Transfer", "Payment", "გადახდა"]
AMBIGUITY = {"salary": .3, "harvest": .2, "p2p_in": .3, "remittance": .1, "own_transfer": .4, "one_off_in": .4,
             "savings": .3, "card_spend": .15, "utilities": .1, "loan_repayment": .3, "betting": .3, "p2p_out": .3}


def sigmoid(x):
    return 1.0 / (1.0 + np.exp(-x))


def annuity(principal, annual_rate, term_months):
    r = np.asarray(annual_rate, dtype=float) / 12.0
    return principal * r / (1.0 - (1.0 + r) ** -np.asarray(term_months, dtype=float))


def expected_profile(archetype: str, monthly_income: float) -> np.ndarray:
    """Expected income by calendar month (Jan..Dec), averaging to monthly_income."""
    h = ARCHETYPES[archetype]["harvest"]
    prof = np.full(12, monthly_income, dtype=float)
    if h:
        prof = np.full(12, 0.3 * monthly_income)
        for m in h:
            prof[m - 1] += 0.7 * monthly_income * 12 / len(h)
    return prof


def liquidity_stress(payments_by_month: np.ndarray, income_by_month: np.ndarray) -> float:
    """Worst rolling-3-month ratio of debt payments to income over a 12-month cycle."""
    p = np.concatenate([payments_by_month, payments_by_month[:2]])
    i = np.concatenate([income_by_month, income_by_month[:2]])
    return float(max(p[k:k + 3].sum() / max(i[k:k + 3].sum(), 1e-9) for k in range(12)))


INTERCEPT = -3.5


def true_logit(burden, stress, fx_mismatch, gambling_share, late_rate, fragility, shock, savings_rate, drift=0.0):
    """Ground-truth default mechanism (non-linear, with interactions, as in real credit data).
    Published in the data card; never used by the model."""
    return (INTERCEPT + 2.5 * (burden - 0.35) + 2.5 * np.maximum(0.0, burden - 0.6)
            + 1.2 * np.maximum(0.0, stress - 0.6) + 0.9 * fx_mismatch
            + 2.0 * gambling_share + 4.0 * gambling_share * (savings_rate < 0.03)
            + 4.0 * np.maximum(0.0, late_rate - 0.15) - 6.0 * np.minimum(savings_rate, 0.10)
            + fragility + 1.6 * shock + drift)


@dataclass
class Synth:
    borrowers: pd.DataFrame
    transactions: pd.DataFrame
    card: dict


def generate(n: int = 8000, seed: int = 42) -> Synth:
    rng = np.random.default_rng(seed)
    names = list(ARCHETYPES)
    arch = rng.choice(names, size=n, p=[ARCHETYPES[a]["share"] for a in names])
    P = pd.DataFrame([ARCHETYPES[a] for a in arch])
    cohort = np.where(rng.random(n) < 0.55, "A", "B")           # A: apply Jul-2025, B: Jul-2026
    app_date = np.where(cohort == "A", "2025-07-01", "2026-07-01")
    drift = np.where(cohort == "B", 0.15, 0.0)                  # mild deterioration in later cohort

    true_inc = np.round(P["median"].to_numpy() * np.exp(rng.normal(0, P["sigma"].to_numpy())), 0)
    fragility = rng.normal(0, 0.8, n)                            # LATENT: never observed directly
    round_trip = rng.random(n) < 0.025                           # income-faking fraud
    fragility = fragility + 1.0 * round_trip
    fake_mult = np.where(round_trip, rng.uniform(0.4, 1.0, n), 0.0)
    visible = np.where(rng.random(n) < 0.25, rng.uniform(0.6, 0.95, n), 1.0)
    gambler = rng.random(n) < (0.06 + 0.04 * (fragility > 1))
    gamble_share = np.where(gambler, rng.uniform(0.05, 0.30, n), 0.0)
    late_rate = np.clip(sigmoid(-2.2 + 0.9 * fragility + rng.normal(0, 0.6, n)), 0, 1)
    savings_rate = np.clip(0.07 - 0.04 * fragility + rng.normal(0, 0.03, n), 0, 0.3)
    other_pmt = np.where(rng.random(n) < 0.4, true_inc * rng.uniform(0.05, 0.25, n), 0.0).round(0)
    age = np.where(arch == "young_first_loan", rng.integers(19, 26, n), rng.integers(24, 66, n))
    gender = rng.choice(["F", "M"], n)
    thin = rng.random(n) < P["thin"].to_numpy()
    bureau = np.where(thin, np.nan,
                      np.round(720 - 55 * fragility - 160 * late_rate - 70 * gambler + rng.normal(0, 35, n)))

    # ---------------- transactions (vectorised month by month) ----------------
    employer = rng.integers(0, 400, n)
    buyer = rng.integers(0, 25, n)
    chunks = []
    inc_mat = np.zeros((n, OBS_MONTHS))
    harvest_flags = [set(ARCHETYPES[a]["harvest"]) for a in arch]
    remit = P["remit"].to_numpy()
    vol = P["vol"].to_numpy()
    cash = np.clip(rng.normal(P["cash"].to_numpy(), 0.08), 0, 0.7)
    rt_mode = rng.choice(["fast", "slow", "other_cp"], n, p=[0.6, 0.25, 0.15])
    spend_prop = np.exp(rng.normal(0, 0.35, n))   # people with the same income spend very differently

    def add(mask, cat, amount, day, ccy, cp, rt=None):
        idx = np.flatnonzero(mask)
        if idx.size == 0:
            return
        k = rng.integers(0, len(DESC[cat]), idx.size)
        desc = np.array(DESC[cat], dtype=object)[k]
        amb = rng.random(idx.size) < AMBIGUITY.get(cat, 0)
        generic = np.array(GENERIC_IN if np.mean(amount[idx]) > 0 else GENERIC_OUT, dtype=object)
        desc[amb] = generic[rng.integers(0, len(generic), amb.sum())]
        chunks.append(pd.DataFrame({
            "borrower_id": idx, "month_idx": j, "day": day[idx],
            "amount": np.round(amount[idx], 2), "currency": ccy,
            "counterparty": cp[idx] if isinstance(cp, np.ndarray) else cp,
            "description": desc,
            "category_true": cat,
            "is_round_trip": False if rt is None else rt[idx],
        }))

    for j in range(OBS_MONTHS):
        cal_month = j % 12 + 1                        # windows start in January
        d = lambda lo=1, hi=28: rng.integers(lo, hi, n)
        inc = true_inc * np.exp(rng.normal(0, vol))
        is_h = np.array([cal_month in h for h in harvest_flags])
        has_h = np.array([len(h) > 0 for h in harvest_flags])
        inc = np.where(has_h, inc * 0.3 + np.where(is_h, inc * 0.7 * 12 / 3, 0.0), inc)
        inc_mat[:, j] = inc
        local = (inc - inc * remit) * (1 - cash) * visible
        sal = np.isin(arch, ["salaried_tbilisi", "young_first_loan"])
        add(sal & (local > 1), "salary", local, d(1, 6), "GEL", np.char.add("EMP", employer.astype(str)))
        add((arch == "farmer_kakheti") & is_h, "harvest", local * 0.85, d(), "GEL", np.char.add("WINERY", buyer.astype(str)))
        add((arch == "farmer_kakheti") & (local > 1), "p2p_in", np.where(is_h, local * 0.15, local), d(), "GEL",
            np.char.add("P", rng.integers(0, 10**6, n).astype(str)))
        for share in (0.5, 0.3, 0.2):                 # self-employed / remittance households: several clients
            m = np.isin(arch, ["self_employed", "remittance_hh"]) & (local > 1)
            add(m, "p2p_in", local * share * rng.uniform(0.8, 1.2, n), d(), "GEL",
                np.char.add("P", rng.integers(0, 10**6, n).astype(str)))
        add(inc * remit > 1, "remittance", inc * remit / USD_GEL, d(), "USD", "MTO")
        # noise that is NOT income
        ot = rng.random(n) < 0.25
        amt = true_inc * rng.uniform(0.2, 1.0, n)
        add(ot, "own_transfer", amt, d(), "GEL", "SELF")
        add(ot, "own_transfer", -amt, d(), "GEL", "SELF")
        add(rng.random(n) < 0.03, "one_off_in", true_inc * rng.uniform(2, 6, n), d(), "GEL",
            np.char.add("P", rng.integers(0, 10**6, n).astype(str)))
        # round-trip fraud: money in from a friend, sent back days later
        rt_m = round_trip & (rng.random(n) < 0.85)
        fake = true_inc * fake_mult * rng.uniform(0.8, 1.2, n)
        rt_day = d(1, 14)
        rt_cp = np.char.add("RT", np.arange(n).astype(str))
        lag = np.where(rt_mode == "slow", rng.integers(8, 15, n), rng.integers(1, 6, n))
        back_cp = np.where(rt_mode == "other_cp", np.char.add("RTX", np.arange(n).astype(str)), rt_cp)
        add(rt_m, "p2p_in", fake, rt_day, "GEL", rt_cp, rt=round_trip)
        add(rt_m, "p2p_out", -fake * rng.uniform(0.97, 1.0, n), rt_day + lag, "GEL", back_cp, rt=round_trip)
        # legitimate refunds look exactly like round trips (source of false positives)
        rf = rng.random(n) < 0.006
        rf_cp = np.char.add("P", rng.integers(0, 10**6, n).astype(str))
        rf_amt = true_inc * rng.uniform(0.05, 0.3, n)
        add(rf, "p2p_in", rf_amt, rt_day, "GEL", rf_cp)
        add(rf, "p2p_out", -rf_amt, rt_day + rng.integers(1, 6, n), "GEL", rf_cp)
        # spending
        for share in (0.15, 0.12, 0.08):
            add(np.ones(n, bool), "card_spend", -true_inc * share * spend_prop * (1 - 0.6 * cash) * rng.uniform(0.7, 1.3, n), d(), "GEL", "MERCHANT")
        for _ in range(2):
            late = rng.random(n) < late_rate
            add(np.ones(n, bool), "utilities", -rng.uniform(30, 90, n), np.where(late, d(20, 29), d(1, 11)), "GEL", "UTILITY")
        add(other_pmt > 0, "loan_repayment", -other_pmt, d(), "GEL", "LENDER")
        add(gambler, "betting", -true_inc * gamble_share * rng.uniform(0.6, 1.4, n), d(), "GEL", "BET")
        add((savings_rate > 0.005) & (rng.random(n) < 0.75), "savings", -true_inc * savings_rate, d(), "GEL", "SELF-SAV")
        add(rng.random(n) < 0.5, "p2p_out", -true_inc * rng.uniform(0.02, 0.1, n), d(), "GEL",
            np.char.add("P", rng.integers(0, 10**6, n).astype(str)))

    tx = pd.concat(chunks, ignore_index=True)
    base_year = np.where(cohort == "A", 2024, 2025)[tx["borrower_id"].to_numpy()]
    tx["date"] = pd.to_datetime(pd.DataFrame({"year": base_year + tx["month_idx"] // 12,
                                              "month": tx["month_idx"] % 12 + 1,
                                              "day": np.clip(tx["day"], 1, 28)}))
    tx = tx.drop(columns=["day"]).sort_values(["borrower_id", "date"]).reset_index(drop=True)
    tx.insert(0, "tx_id", np.arange(len(tx)))

    # ---------------- application ----------------
    declared = np.round((true_inc + true_inc * fake_mult) * np.exp(rng.normal(P["bias"].to_numpy(), 0.15)), 0)
    currency = np.where((remit > 0.5) & (rng.random(n) < 0.3), "USD",
                        np.where(rng.random(n) < 0.04, "USD", "GEL"))
    income_ccy = np.where(remit > 0.5, "USD", "GEL")
    amount = np.round(declared * rng.uniform(3, 10, n), -2)
    term = rng.choice([12, 24, 36, 48, 60], n)
    rate = np.where(currency == "GEL", rng.uniform(0.15, 0.24, n), rng.uniform(0.08, 0.12, n)) + 0.01 * (cohort == "B")
    payment = annuity(amount, rate, term)
    has_coll = rng.random(n) < 0.30
    collateral = np.where(has_coll, amount / rng.uniform(0.4, 0.95, n), np.nan).round(-2)

    # ---------------- outcome (12 months after application) ----------------
    shock = rng.random(n) < P["shock"].to_numpy()
    burden = (other_pmt + payment) / true_inc
    stress = np.array([liquidity_stress(np.full(12, other_pmt[i] + payment[i]), expected_profile(arch[i], true_inc[i]))
                       for i in range(n)])
    fx_mis = (currency == "USD") & (income_ccy == "GEL")
    logit = true_logit(burden, stress, fx_mis, gamble_share, late_rate, fragility, shock, savings_rate, drift)
    pd_true = sigmoid(logit)
    default = rng.random(n) < pd_true

    bor = pd.DataFrame({
        "borrower_id": np.arange(n), "cohort": cohort, "application_date": app_date,
        "archetype": arch, "region": P["region"].to_numpy(), "age": age, "gender": gender,
        "thin_file": thin, "bureau_score": bureau, "declared_income_gel": declared,
        "income_currency": income_ccy, "loan_amount_gel": amount, "loan_currency": currency,
        "term_months": term, "annual_rate": rate.round(4), "monthly_payment_gel": payment.round(2),
        "existing_debt_payment_declared": np.round(other_pmt * rng.uniform(0.7, 1.0, n), 0),
        "collateral_value_gel": collateral,
        # ---------- HIDDEN GROUND TRUTH ----------
        "TRUE_income_gel": true_inc, "TRUE_fragility": fragility.round(3), "TRUE_round_trip": round_trip,
        "TRUE_shock": shock, "TRUE_burden": burden.round(4), "TRUE_stress": stress.round(4),
        "TRUE_gamble_share": gamble_share.round(4), "TRUE_late_rate": late_rate.round(4),
        "TRUE_savings_rate": savings_rate.round(4), "TRUE_cash_share": cash.round(3),
        "TRUE_other_payment": other_pmt, "TRUE_pd": pd_true.round(5), "TRUE_default": default,
    })
    card = {
        "synthetic": True, "generator_version": "2.0", "seed": seed, "n_borrowers": n,
        "n_transactions": int(len(tx)), "observation_months": OBS_MONTHS, "usd_gel": USD_GEL,
        "default_rate": float(round(default.mean(), 4)),
        "default_rate_by_cohort": bor.groupby("cohort")["TRUE_default"].mean().round(4).to_dict(),
        "round_trip_share": float(round(round_trip.mean(), 4)),
        "thin_file_share": float(round(thin.mean(), 4)),
        "pd_mechanism": (f"sigmoid({INTERCEPT} + 2.5*(burden-0.35) + 2.5*max(0,burden-0.6) + 1.2*max(0,stress-0.6) "
                         "+ 0.9*fx_mismatch + 2*gambling + 4*gambling*(savings<3%) + 4*max(0,late_rate-0.15) "
                         "- 6*min(savings,10%) + fragility + 1.6*shock + drift)"),
        "unobservable_drivers": ["fragility (latent trait)", "post-application shock", "cash income",
                                 "income at other banks"],
        "archetypes": {k: {kk: (list(vv) if isinstance(vv, tuple) else vv) for kk, vv in v.items()}
                       for k, v in ARCHETYPES.items()},
        "calibration_sources_to_replace": ["Geostat average wages by region", "Geostat Integrated Household Survey",
                                           "NBG USD/GEL monthly rates", "NBG retail loan interest rates"],
    }
    return Synth(bor, tx, card)


def save(s: Synth, out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    s.borrowers.to_csv(out / "borrowers.csv", index=False)
    s.transactions.to_parquet(out / "transactions.parquet", index=False)
    (out / "data_card.json").write_text(json.dumps(s.card, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=8000)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", default="data")
    a = ap.parse_args()
    s = generate(a.n, a.seed)
    save(s, Path(a.out))
    print(json.dumps({k: s.card[k] for k in ("n_borrowers", "n_transactions", "default_rate",
                                             "default_rate_by_cohort", "round_trip_share", "thin_file_share")}, indent=1))
