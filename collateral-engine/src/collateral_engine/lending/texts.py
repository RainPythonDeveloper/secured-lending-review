"""Georgian and English texts of the loan application pipeline."""

from collateral_engine.i18n import Bilingual, Language
from collateral_engine.lending.affordability import LoanProduct
from collateral_engine.lending.customer import CustomerProfile, DataSource
from collateral_engine.lending.decision import LoanDecisionKind
from collateral_engine.lending.pipeline import (
    BindingLimit,
    Finding,
    LendingReason,
    LendingRecommendation,
    StageKind,
    StageStatus,
)

KA, EN = Language.GEORGIAN, Language.ENGLISH

LENDING_REASON_TEMPLATES: dict[LendingReason, Bilingual] = {
    LendingReason.IDENTITY_CONFIRMED: {
        KA: "პირი იდენტიფიცირებულია; სანქციების სიებსა და მოვალეთა რეესტრში ჩანაწერი არ არის.",
        EN: "Identity confirmed; no record on the sanctions lists or in the debtors registry.",
    },
    LendingReason.SANCTIONS_MATCH: {
        KA: "სახელი ემთხვევა ჩანაწერს სიაში „{list}“; საჭიროა შესაბამისობის შემოწმება.",
        EN: "The name matches an entry on '{list}'; compliance must check it.",
    },
    LendingReason.DEBTORS_REGISTRY_RECORD: {
        KA: "მოვალეთა რეესტრში ჩანაწერია: {case}, {amount} ლარი.",
        EN: "Debtors registry record: {case}, {amount} GEL.",
    },
    LendingReason.THIN_FILE: {
        KA: "საკრედიტო ისტორია არ არის; შემოსავალი ანგარიშების მონაცემებით მოწმდება.",
        EN: "No credit history (thin file); income is checked from account data instead.",
    },
    LendingReason.CREDIT_HISTORY_CLEAN: {
        KA: "საკრედიტო ისტორია სუფთაა, მიმდინარე ვალდებულებები არ არის.",
        EN: "Clean credit history with no current obligations.",
    },
    LendingReason.EXISTING_OBLIGATIONS: {
        KA: "{count} მიმდინარე ვალდებულება, თვეში ჯამში {payment} ლარი — ითვლება PTI-ში.",
        EN: "{count} current obligation(s), {payment} GEL a month in total; counted in PTI.",
    },
    LendingReason.DAYS_PAST_DUE: {
        KA: "ბოლო 12 თვეში გადახდა {days} დღით იყო ვადაგადაცილებული.",
        EN: "A payment was {days} days past due in the last 12 months.",
    },
    LendingReason.INCOME_VERIFIED: {
        KA: "ანგარიშებით დადასტურებული შემოსავალი: {verified} ლარი თვეში ({months} თვე); PTI-სთვის "
        "კონსერვატიული შეფასება {conservative} ლარი.",
        EN: "Income confirmed from accounts: {verified} GEL a month over {months} months; PTI "
        "uses the conservative {conservative} GEL.",
    },
    LendingReason.DECLARED_ABOVE_VERIFIED: {
        KA: "დეკლარირებული შემოსავალი ({declared} ლარი) {gap}%-ით აღემატება დადასტურებულს "
        "({verified} ლარი).",
        EN: "Declared income ({declared} GEL) is {gap}% above the confirmed {verified} GEL.",
    },
    LendingReason.INCOME_UNSTABLE: {
        KA: "შემოსავალი არასტაბილურია: თვიური ცვალებადობა {variation}%.",
        EN: "Unstable income: month-to-month variation of {variation}%.",
    },
    LendingReason.INCOME_HISTORY_SHORT: {
        KA: "შემოსავალი მხოლოდ {months} თვეშია; საჭიროა დამატებითი დოკუმენტები.",
        EN: "Income in only {months} months; more documents are needed.",
    },
    LendingReason.UNDOCUMENTED_INCOME: {
        KA: "შემოსავალი შემოსავლების სამსახურში (RS.ge) დოკუმენტირებული არ არის; ანგარიშების "
        "მონაცემები ავსებს ამ ხარვეზს.",
        EN: "The income is not documented with the Revenue Service (RS.ge); account data fills "
        "the gap.",
    },
    LendingReason.PTI_WITHIN_LIMIT: {
        KA: "PTI {pti}% სებ-ის {limit}%-იანი ლიმიტის ფარგლებშია; მაქსიმუმი {max_amount} ლარი.",
        EN: "PTI {pti}% is within the NBG limit of {limit}%; at most {max_amount} GEL.",
    },
    LendingReason.PTI_ABOVE_LIMIT: {
        KA: "მოთხოვნილ თანხაზე PTI {pti}% აჭარბებს სებ-ის {limit}%-იან ლიმიტს; შეთავაზება "
        "მცირდება {max_amount} ლარამდე.",
        EN: "PTI {pti}% on the requested amount exceeds the NBG limit of {limit}%; the offer is "
        "cut to {max_amount} GEL.",
    },
    LendingReason.CURRENCY_MUST_BE_GEL: {
        KA: "{threshold} ლარზე ნაკლები სესხი ლარში უნდა გაიცეს, რადგან შემოსავალი ლარშია (სებ).",
        EN: "A loan below {threshold} GEL must be in GEL because the income is in GEL (NBG).",
    },
    LendingReason.TERM_ABOVE_MAXIMUM: {
        KA: "{term} თვის ვადა აღემატება სებ-ის მაქსიმუმს ({max_term} თვე); შეთავაზება "
        "{max_term} თვეზეა.",
        EN: "A {term}-month term is above the NBG maximum of {max_term} months; the offer uses "
        "{max_term} months.",
    },
    LendingReason.NO_COLLATERAL_NEEDED: {
        KA: "სესხი უზრუნველყოფის გარეშეა.",
        EN: "Unsecured loan: no collateral.",
    },
    LendingReason.COLLATERAL_VALUED: {
        KA: "გირაოს ღირებულება {value} USD; LTV-ით მაქსიმუმი {max_loan} {currency}.",
        EN: "Collateral worth {value} USD; at most {max_loan} {currency} under LTV.",
    },
    LendingReason.COLLATERAL_REVIEW: {
        KA: "გირაო შეფასდა ({value} USD, LTV-ით მაქსიმუმი {max_loan} {currency}), მაგრამ ოფიცერმა "
        "უნდა შეამოწმოს ფოტოები, მდგომარეობა ან შემფასებლის ანგარიში.",
        EN: "Collateral valued at {value} USD (at most {max_loan} {currency} under LTV), but the "
        "officer must check the photos, the condition or the valuer's figure.",
    },
    LendingReason.COLLATERAL_INSPECTION: {
        KA: "გირაოს ({value} USD) ადგილზე დათვალიერებაა საჭირო; LTV-ით მაქსიმუმი {max_loan} "
        "{currency}.",
        EN: "The collateral ({value} USD) needs a physical inspection; at most {max_loan} "
        "{currency} under LTV.",
    },
    LendingReason.COLLATERAL_NOT_VALUED: {
        KA: "გირაო ვერ შეფასდა; საჭიროა შემფასებელი.",
        EN: "The collateral could not be valued; a valuer is needed.",
    },
}

STAGE_NAMES: dict[StageKind, Bilingual] = {
    StageKind.IDENTITY: {KA: "იდენტიფიკაცია და სიები", EN: "Identity and watchlists"},
    StageKind.CREDIT_HISTORY: {KA: "საკრედიტო ისტორია", EN: "Credit history"},
    StageKind.INCOME: {KA: "შემოსავალი", EN: "Income"},
    StageKind.AFFORDABILITY: {KA: "გადახდისუნარიანობა (სებ)", EN: "Affordability (NBG)"},
    StageKind.COLLATERAL: {KA: "გირაო (LTV)", EN: "Collateral (LTV)"},
}

STAGE_STATUS_NAMES: dict[StageStatus, Bilingual] = {
    StageStatus.PASSED: {KA: "გავლილია", EN: "Passed"},
    StageStatus.INFO: {KA: "შენიშვნა", EN: "Note"},
    StageStatus.REVIEW: {KA: "განხილვა", EN: "Review"},
    StageStatus.NOT_APPLICABLE: {KA: "არ ეხება", EN: "Not applicable"},
}

LENDING_RECOMMENDATION_NAMES: dict[LendingRecommendation, Bilingual] = {
    LendingRecommendation.OFFER: {
        KA: "შეთავაზება მოთხოვნილი თანხით",
        EN: "Offer the requested amount",
    },
    LendingRecommendation.OFFER_REDUCED: {
        KA: "შეთავაზება შემცირებული თანხით",
        EN: "Offer a reduced amount",
    },
    LendingRecommendation.OFFICER_REVIEW: {
        KA: "საჭიროა ოფიცრის განხილვა",
        EN: "Officer review needed",
    },
    LendingRecommendation.COMPLIANCE_REVIEW: {
        KA: "საჭიროა შესაბამისობის შემოწმება",
        EN: "Compliance review needed",
    },
    LendingRecommendation.PHYSICAL_INSPECTION: {
        KA: "საჭიროა გირაოს დათვალიერება",
        EN: "Physical inspection of the collateral needed",
    },
}

LOAN_PRODUCT_NAMES: dict[LoanProduct, Bilingual] = {
    LoanProduct.CONSUMER: {KA: "სამომხმარებლო სესხი", EN: "Consumer loan"},
    LoanProduct.MORTGAGE: {KA: "იპოთეკა", EN: "Mortgage"},
    LoanProduct.AUTO: {KA: "ავტოსესხი", EN: "Car loan"},
}

DATA_SOURCE_NAMES: dict[DataSource, Bilingual] = {
    DataSource.OPEN_BANKING: {
        KA: "Open Banking · TBC sandbox-ის თანხმობა",
        EN: "Open Banking · TBC sandbox consent",
    },
    DataSource.BANK_SNAPSHOT: {
        KA: "ბანკის ჩანაწერები (Open Banking-ის გარეშე)",
        EN: "Bank records (without Open Banking)",
    },
    DataSource.SYNTHETIC_APPLICANT: {
        KA: "სინთეტიკური განმცხადებელი",
        EN: "Synthetic applicant",
    },
}

CUSTOMER_PROFILE_NAMES: dict[CustomerProfile, Bilingual] = {
    CustomerProfile.SALARIED: {KA: "დაქირავებული", EN: "Salaried"},
    CustomerProfile.PROFESSIONAL: {KA: "პროფესიონალი", EN: "Professional"},
    CustomerProfile.FREELANCER: {KA: "ფრილანსერი", EN: "Freelancer"},
    CustomerProfile.RETIRED: {KA: "პენსიონერი", EN: "Retired"},
    CustomerProfile.STUDENT: {KA: "სტუდენტი", EN: "Student"},
    CustomerProfile.SELF_EMPLOYED: {KA: "თვითდასაქმებული", EN: "Self-employed"},
    CustomerProfile.SEASONAL_WORKER: {KA: "სეზონური მუშაკი", EN: "Seasonal worker"},
}

LENDING_BINDING_NAMES: dict[BindingLimit, Bilingual] = {
    BindingLimit.REQUEST: {KA: "მოთხოვნილი თანხა", EN: "The requested amount"},
    BindingLimit.PTI: {KA: "შემოსავალი (PTI)", EN: "Income (PTI)"},
    BindingLimit.LTV: {KA: "გირაო (LTV)", EN: "Collateral (LTV)"},
}

LOAN_DECISION_NAMES: dict[LoanDecisionKind, Bilingual] = {
    LoanDecisionKind.APPROVE: {KA: "დამტკიცება", EN: "Approve"},
    LoanDecisionKind.APPROVE_REDUCED: {
        KA: "დამტკიცება შემცირებული თანხით",
        EN: "Approve a reduced amount",
    },
    LoanDecisionKind.REQUEST_DOCUMENTS: {KA: "დოკუმენტების მოთხოვნა", EN: "Request documents"},
    LoanDecisionKind.DECLINE: {KA: "უარი (ოფიცრის გადაწყვეტილება)", EN: "Decline (officer)"},
}


def finding_text(finding: Finding, language: Language) -> str:
    return LENDING_REASON_TEMPLATES[finding.reason][language].format(**finding.params)
