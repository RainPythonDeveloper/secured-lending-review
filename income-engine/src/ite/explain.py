"""Per-applicant reasons (SHAP) in plain Georgian and English, plus the borrower letter."""
from __future__ import annotations

import numpy as np
import pandas as pd
import shap

# feature -> (English if it raises risk, English if it lowers risk, Georgian raise, Georgian lower)
REASONS = {
    "pti_est": ("Loan payments take a large share of income", "Loan payments are a comfortable share of income",
                "სესხის გადასახადი შემოსავლის დიდ ნაწილს შეადგენს", "სესხის გადასახადი შემოსავალთან შედარებით დაბალია"),
    "stress_est": ("Payments are hard to cover in low-income months", "Payments are covered even in low-income months",
                   "დაბალი შემოსავლის თვეებში გადახდა რთულია", "გადახდა დაფარულია დაბალი შემოსავლის თვეებშიც"),
    "burden_p25": ("Payment is high versus a conservative income estimate", "Payment is affordable on a conservative income estimate",
                   "გადასახადი მაღალია კონსერვატიულ შემოსავალთან", "გადასახადი ხელმისაწვდომია კონსერვატიული შეფასებითაც"),
    "inc_cv": ("Income varies a lot from month to month", "Income is stable from month to month",
               "შემოსავალი თვიდან თვემდე ძლიერ იცვლება", "შემოსავალი სტაბილურია"),
    "season_top3": ("Most income arrives in a few months of the year", "Income is spread across the year",
                    "შემოსავლის უმეტესი ნაწილი წლის რამდენიმე თვეში შემოდის", "შემოსავალი წლის განმავლობაში თანაბრადაა გადანაწილებული"),
    "betting_share": ("Regular spending on betting or casinos", "No significant betting spend",
                      "რეგულარული ხარჯი ტოტალიზატორზე / კაზინოზე", "ტოტალიზატორზე ხარჯი არ ფიქსირდება"),
    "late_util_rate": ("Utility bills are often paid late", "Utility bills are paid on time",
                       "კომუნალური გადასახადები ხშირად გვიან იხდება", "კომუნალური გადასახადები დროულად იხდება"),
    "savings_rate": ("Little or no regular saving", "Saves regularly",
                     "რეგულარული დანაზოგი არ ფიქსირდება", "რეგულარულად ზოგავს"),
    "circular_ratio": ("Some incoming money is sent straight back (possible income inflation)", "No circular transfers",
                       "შემოსული თანხის ნაწილი მალევე უკან იგზავნება", "წრიული გადარიცხვები არ ფიქსირდება"),
    "bureau_score": ("Weaker credit bureau history", "Good credit bureau history",
                     "საკრედიტო ისტორია სუსტია", "საკრედიტო ისტორია კარგია"),
    "thin_file": ("No credit bureau history", "Has credit bureau history",
                  "საკრედიტო ისტორია არ არსებობს", "საკრედიტო ისტორია არსებობს"),
    "fx_mismatch": ("Loan in USD while income is in GEL (currency risk)", "No currency mismatch",
                    "სესხი დოლარშია, შემოსავალი ლარში (სავალუტო რისკი)", "სავალუტო შეუსაბამობა არ არის"),
    "declared_gap": ("Declared income differs from income seen in accounts", "Declared income matches account data",
                     "დეკლარირებული შემოსავალი არ ემთხვევა ანგარიშის მონაცემებს", "დეკლარირებული შემოსავალი ემთხვევა ანგარიშის მონაცემებს"),
    "band_width": ("Income estimate is uncertain", "Income estimate is precise",
                   "შემოსავლის შეფასება გაურკვეველია", "შემოსავლის შეფასება ზუსტია"),
    "spend_ratio": ("High everyday spending relative to income", "Moderate everyday spending",
                    "ყოველდღიური ხარჯი მაღალია შემოსავალთან შედარებით", "ყოველდღიური ხარჯი ზომიერია"),
    "loan_to_income": ("Loan is large relative to income", "Loan is modest relative to income",
                       "სესხი დიდია შემოსავალთან შედარებით", "სესხი ზომიერია შემოსავალთან შედარებით"),
}


class Explainer:
    """Explains the CHAMPION model: exact linear contributions for the scorecard, SHAP for the GBM."""

    def __init__(self, risk_model):
        self.rm = risk_model
        self.exp = shap.TreeExplainer(risk_model.lgbm) if risk_model.champion == "gbm" else None

    def values(self, X: pd.DataFrame) -> np.ndarray:
        from .models import RISK_FEATURES
        X = X[RISK_FEATURES]
        if self.exp is None:
            return self.rm.scorecard.contributions(X)
        sv = self.exp.shap_values(X)
        return sv[1] if isinstance(sv, list) else sv

    def reasons(self, X_row: pd.DataFrame, k: int = 4) -> list[dict]:
        sv = self.values(X_row)[0]
        order = np.argsort(-np.abs(sv))
        out = []
        for i in order:
            f = X_row.columns[i]
            if f not in REASONS or abs(sv[i]) < 0.05:
                continue
            up = sv[i] > 0
            en_up, en_dn, ka_up, ka_dn = REASONS[f]
            out.append({"feature": f, "value": _num(X_row.iloc[0, i]), "impact": float(sv[i]),
                        "direction": "raises risk" if up else "lowers risk",
                        "en": en_up if up else en_dn, "ka": ka_up if up else ka_dn})
            if len(out) == k:
                break
        return out


def _num(v):
    try:
        return None if pd.isna(v) else float(v)
    except (TypeError, ValueError):
        return v


def borrower_letter(decision: dict, lang: str = "ka") -> str:
    """Template-filled letter: every number comes from the decision record, no free-form generation."""
    o = decision["offer"]
    reasons = decision["reasons"][:3]
    if lang == "ka":
        head = {"APPROVE": "თქვენი სესხის განაცხადი დამტკიცებულია.",
                "APPROVE_REDUCED": f"შეგვიძლია შემოგთავაზოთ {o['amount']:,.0f} ლარი {o['term_months']} თვით.",
                "REVIEW": "თქვენს განაცხადს განიხილავს საკრედიტო ოფიცერი.",
                "REFER": "თქვენს განაცხადს დამატებით განიხილავს საკრედიტო ოფიცერი."}[decision["recommendation"]]
        body = "\n".join(f"• {r['ka']}" for r in reasons)
        tail = ("\nშეთავაზება შეესაბამება საქართველოს ეროვნული ბანკის პასუხისმგებლიანი დაკრედიტების მოთხოვნებს. "
                "გადაწყვეტილებას იღებს ბანკის თანამშრომელი.")
        return f"{head}\n\nმთავარი ფაქტორები:\n{body}{tail}"
    head = {"APPROVE": "Your loan application is approved.",
            "APPROVE_REDUCED": f"We can offer {o['amount']:,.0f} GEL over {o['term_months']} months.",
            "REVIEW": "Your application will be reviewed by a loan officer.",
            "REFER": "Your application needs a further review by a loan officer."}[decision["recommendation"]]
    body = "\n".join(f"• {r['en']}" for r in reasons)
    return (f"{head}\n\nMain factors:\n{body}\nThe offer follows the National Bank of Georgia's responsible-lending "
            "rules. A bank officer makes the final decision.")
