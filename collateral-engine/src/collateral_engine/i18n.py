"""Texts for people, in Georgian and English. Messages are templates filled with report values;
no free-form model text is shown as a reason. Have a native speaker review the Georgian copy."""

from enum import StrEnum

from collateral_engine.domain import BuildingStatus, ClaimStatus, Condition, ConstructionStage
from collateral_engine.flags import Flag, ReasonCode, Recommendation, Severity
from collateral_engine.report import AppraisalPosition, LendingValueBasis
from collateral_engine.report_check import ReportFinding, ReportIssue


class Language(StrEnum):
    GEORGIAN = "ka"
    ENGLISH = "en"


type Bilingual = dict[Language, str]

CONDITION_NAMES: dict[Condition, Bilingual] = {
    Condition.BLACK_FRAME: {Language.GEORGIAN: "შავი კარკასი", Language.ENGLISH: "Black frame"},
    Condition.WHITE_FRAME: {Language.GEORGIAN: "თეთრი კარკასი", Language.ENGLISH: "White frame"},
    Condition.GREEN_FRAME: {Language.GEORGIAN: "მწვანე კარკასი", Language.ENGLISH: "Green frame"},
    Condition.NEEDS_RENOVATION: {
        Language.GEORGIAN: "სარემონტო",
        Language.ENGLISH: "Needs renovation",
    },
    Condition.UNDER_RENOVATION: {
        Language.GEORGIAN: "მიმდინარე რემონტი",
        Language.ENGLISH: "Under renovation",
    },
    Condition.OLD_RENOVATED: {
        Language.GEORGIAN: "ძველი გარემონტებული",
        Language.ENGLISH: "Old renovation",
    },
    Condition.NEWLY_RENOVATED: {
        Language.GEORGIAN: "ახალი გარემონტებული",
        Language.ENGLISH: "Newly renovated",
    },
}

BUILDING_STATUS_NAMES: dict[BuildingStatus, Bilingual] = {
    BuildingStatus.NEW_BUILDING: {
        Language.GEORGIAN: "ახალი აშენებული",
        Language.ENGLISH: "New building",
    },
    BuildingStatus.OLD_BUILDING: {
        Language.GEORGIAN: "ძველი აშენებული",
        Language.ENGLISH: "Old building",
    },
    BuildingStatus.UNDER_CONSTRUCTION: {
        Language.GEORGIAN: "მშენებარე",
        Language.ENGLISH: "Under construction",
    },
}

CONSTRUCTION_STAGE_NAMES: dict[ConstructionStage, Bilingual] = {
    ConstructionStage.FOUNDATION: {Language.GEORGIAN: "საძირკველი", Language.ENGLISH: "Foundation"},
    ConstructionStage.STRUCTURAL_FRAME: {
        Language.GEORGIAN: "კონსტრუქციული კარკასი",
        Language.ENGLISH: "Structural frame",
    },
    ConstructionStage.WALLS_AND_ROOF: {
        Language.GEORGIAN: "კედლები და სახურავი",
        Language.ENGLISH: "Walls and roof closed",
    },
    ConstructionStage.FINISHING: {
        Language.GEORGIAN: "მოპირკეთების სამუშაოები",
        Language.ENGLISH: "Finishing works",
    },
}

CLAIM_STATUS_NAMES: dict[ClaimStatus, Bilingual] = {
    ClaimStatus.VERIFIED: {Language.GEORGIAN: "დადასტურებულია", Language.ENGLISH: "Verified"},
    ClaimStatus.PARTLY: {
        Language.GEORGIAN: "ნაწილობრივ დადასტურებულია",
        Language.ENGLISH: "Partly confirmed",
    },
    ClaimStatus.NOT_VERIFIED: {
        Language.GEORGIAN: "არ არის გადამოწმებული",
        Language.ENGLISH: "Not verified",
    },
    ClaimStatus.CONTRADICTED: {
        Language.GEORGIAN: "ეწინააღმდეგება ფოტოებს",
        Language.ENGLISH: "Contradicted by photos",
    },
    ClaimStatus.INCONCLUSIVE: {Language.GEORGIAN: "გაურკვეველია", Language.ENGLISH: "Inconclusive"},
}

RECOMMENDATION_NAMES: dict[Recommendation, Bilingual] = {
    Recommendation.ACCEPT_VALUATION: {
        Language.GEORGIAN: "შეფასების მიღება",
        Language.ENGLISH: "Accept the valuation",
    },
    Recommendation.OFFICER_REVIEW: {
        Language.GEORGIAN: "საჭიროა ოფიცრის გადამოწმება",
        Language.ENGLISH: "Officer review needed",
    },
    Recommendation.PHYSICAL_INSPECTION: {
        Language.GEORGIAN: "ადგილზე დათვალიერება",
        Language.ENGLISH: "Physical inspection by a valuer",
    },
}

SEVERITY_NAMES: dict[Severity, Bilingual] = {
    Severity.INFO: {Language.GEORGIAN: "ინფორმაცია", Language.ENGLISH: "Info"},
    Severity.REVIEW: {Language.GEORGIAN: "გადამოწმება", Language.ENGLISH: "Review"},
    Severity.PHYSICAL_INSPECTION: {
        Language.GEORGIAN: "დათვალიერება",
        Language.ENGLISH: "Inspection",
    },
}

APPRAISAL_POSITION_NAMES: dict[AppraisalPosition, Bilingual] = {
    AppraisalPosition.WITHIN_RANGE: {
        Language.GEORGIAN: "მოდელის დიაპაზონშია",
        Language.ENGLISH: "Within the model range",
    },
    AppraisalPosition.ABOVE_RANGE: {
        Language.GEORGIAN: "დიაპაზონზე მაღალია",
        Language.ENGLISH: "Above the model range",
    },
    AppraisalPosition.BELOW_RANGE: {
        Language.GEORGIAN: "დიაპაზონზე დაბალია",
        Language.ENGLISH: "Below the model range",
    },
}

LENDING_VALUE_BASIS_NAMES: dict[LendingValueBasis, Bilingual] = {
    LendingValueBasis.MODEL_RANGE_LOW: {
        Language.GEORGIAN: "მოდელის დიაპაზონის ქვედა ზღვარი",
        Language.ENGLISH: "Lower end of the model range",
    },
    LendingValueBasis.LICENSED_APPRAISAL: {
        Language.GEORGIAN: "ლიცენზირებული შემფასებლის შეფასება",
        Language.ENGLISH: "Licensed appraisal",
    },
    LendingValueBasis.MODEL_ESTIMATE: {
        Language.GEORGIAN: "მოდელის შეფასება",
        Language.ENGLISH: "Model estimate",
    },
}

REASON_TEMPLATES: dict[ReasonCode, Bilingual] = {
    ReasonCode.INSUFFICIENT_COMPARABLES: {
        Language.GEORGIAN: "{radius_km} კმ რადიუსში მხოლოდ {found} ანალოგიური გაყიდვაა, რომლის "
        "კორექტირებაც სებ-ის №84/04 ბრძანების ლიმიტებშია (მუხ. 4(5)); "
        "საჭიროა შემფასებლის მიერ ბინის დათვალიერება.",
        Language.ENGLISH: "Only {found} comparable sales within {radius_km} km have adjustments "
        "within the limits of NBG Order 84/04 (Art. 4(5)); a valuer has to inspect the flat.",
    },
    ReasonCode.ADJUSTMENT_JUSTIFICATION_REQUIRED: {
        Language.GEORGIAN: "ანალოგების ჯამური კორექტირება {gross}%-ს აღწევს, რაც {limit}%-იან "
        "ლიმიტს აღემატება (სებ-ის №84/04, მუხ. 4(5)(ბ)); დასაშვებია {justified_limit}%-მდე "
        "მხოლოდ წერილობითი დასაბუთებით.",
        Language.ENGLISH: "Comparable adjustments reach {gross}% gross, above the {limit}% limit "
        "of NBG Order 84/04 Art. 4(5)(b); up to {justified_limit}% is allowed only with a "
        "written justification.",
    },
    ReasonCode.COMPARABLES_WIDENED_RADIUS: {
        Language.GEORGIAN: "საკმარისი ანალოგების მოსაძებნად ძიების რადიუსი "
        "{radius_km} კმ-მდე გაიზარდა.",
        Language.ENGLISH: "The search radius was widened to {radius_km} km to find enough sales.",
    },
    ReasonCode.MODEL_DISAGREEMENT: {
        Language.GEORGIAN: "ანალოგიური გაყიდვებისა და ჰედონური მოდელის შეფასებები "
        "{percent}%-ით განსხვავდება.",
        Language.ENGLISH: "Comparable sales and the hedonic model differ by {percent}%.",
    },
    ReasonCode.APPRAISAL_ABOVE_RANGE: {
        Language.GEORGIAN: "ლიცენზირებული შემფასებლის შეფასება მოდელის შეფასებაზე "
        "{percent}%-ით მაღალია და დიაპაზონს სცდება.",
        Language.ENGLISH: "The licensed appraisal is {percent}% above the model estimate, "
        "outside its range.",
    },
    ReasonCode.APPRAISAL_BELOW_RANGE: {
        Language.GEORGIAN: "ლიცენზირებული შემფასებლის შეფასება მოდელის შეფასებაზე "
        "{percent}%-ით დაბალია და დიაპაზონს სცდება.",
        Language.ENGLISH: "The licensed appraisal is {percent}% below the model estimate, "
        "outside its range.",
    },
    ReasonCode.CONDITION_PARTLY_CONFIRMED: {
        Language.GEORGIAN: "ფოტოებზე ჩანს „{observed}“, დეკლარირებულია „{declared}“; "
        "ბინა შეფასდა ფოტოების მიხედვით.",
        Language.ENGLISH: "Photos show '{observed}', not the declared '{declared}'; "
        "the flat is valued as shown.",
    },
    ReasonCode.CONDITION_CONTRADICTED: {
        Language.GEORGIAN: "ფოტოებზე ჩანს „{observed}“, დეკლარირებულია „{declared}“; "
        "სხვაობა დიდია.",
        Language.ENGLISH: "Photos show '{observed}', far from the declared '{declared}'.",
    },
    ReasonCode.CONDITION_INCONCLUSIVE: {
        Language.GEORGIAN: "ფოტოებით მდგომარეობის დადგენა ვერ მოხერხდა; "
        "ბინა შეფასდა დეკლარირებული მდგომარეობით.",
        Language.ENGLISH: "The photos do not settle the condition; the flat is valued as declared.",
    },
    ReasonCode.CONDITION_NOT_VERIFIED: {
        Language.GEORGIAN: "ფოტოები არ არის წარმოდგენილი; დეკლარირებული მდგომარეობა "
        "გადაუმოწმებელია. საჭიროა ბინის მინიმუმ {required} ფოტო.",
        Language.ENGLISH: "No photos were provided; the declared condition is unverified. "
        "At least {required} photos of the flat are needed.",
    },
    ReasonCode.TOO_FEW_PHOTOS: {
        Language.GEORGIAN: "ატვირთულია {count} ფოტო {required}-დან; მოითხოვეთ ბინის "
        "სხვადასხვა ოთახის მინიმუმ {required} ფოტო.",
        Language.ENGLISH: "{count} of {required} required photos uploaded; ask for at least "
        "{required} photos of different rooms.",
    },
    ReasonCode.PHOTO_QUALITY_ISSUES: {
        Language.GEORGIAN: "{count} ფოტო ძალიან ბნელი, ბუნდოვანი, მცირე ან წაუკითხავია "
        "და არ შეფასებულა.",
        Language.ENGLISH: "{count} photo(s) were too dark, blurred, small or unreadable "
        "and were not assessed.",
    },
    ReasonCode.PHOTOS_WITH_PEOPLE_EXCLUDED: {
        Language.GEORGIAN: "ადამიანების გამოსახულებით {count} ფოტო გამოირიცხა; "
        "მოითხოვეთ ფოტოები ადამიანების გარეშე.",
        Language.ENGLISH: "{count} photo(s) showing people were excluded; "
        "ask for photos without people.",
    },
    ReasonCode.NEAR_DUPLICATE_PHOTOS: {
        Language.GEORGIAN: "განაცხადში {count} წყვილი ფოტო ერთსა და იმავე გამოსახულებას აჩვენებს.",
        Language.ENGLISH: "{count} pair(s) of photos in this application show the same picture.",
    },
    ReasonCode.PHOTO_SEEN_IN_OTHER_APPLICATION: {
        Language.GEORGIAN: "ფოტო ემთხვევა სხვა განაცხადში ({applications}) წარმოდგენილ ფოტოს.",
        Language.ENGLISH: "A photo matches one submitted with application(s) {applications}.",
    },
    ReasonCode.VISION_UNAVAILABLE: {
        Language.GEORGIAN: "{count} ფოტოს ავტომატური ანალიზი ვერ მოხერხდა.",
        Language.ENGLISH: "{count} photo(s) could not be assessed by the vision model.",
    },
    ReasonCode.OFF_PLAN_STAGE_DISCOUNT: {
        Language.GEORGIAN: "დაკრედიტების ღირებულება შემცირებულია {discount}%-ით მშენებლობის "
        "ეტაპის („{stage}“) გამო — დაუსრულებლობის რისკი.",
        Language.ENGLISH: "Lending value reduced by {discount}% for the construction stage "
        "'{stage}': completion risk.",
    },
    ReasonCode.OFF_PLAN_COMPLETION_OVERDUE: {
        Language.GEORGIAN: "დეველოპერის მიერ დაპირებული დასრულების თარიღი ({date}) გასულია; "
        "გადაამოწმეთ მშენებლობა ადგილზე.",
        Language.ENGLISH: "The developer's completion date ({date}) has passed; check the "
        "construction on site.",
    },
    ReasonCode.OFF_PLAN_LONG_COMPLETION: {
        Language.GEORGIAN: "დასრულებამდე {months} თვეა, რაც ბანკის პოლიტიკის {limit} თვეს "
        "აღემატება.",
        Language.ENGLISH: "Completion is {months} months away, beyond the bank's {limit}-month "
        "horizon.",
    },
    ReasonCode.OFF_PLAN_AGREEMENT_NOT_REGISTERED: {
        Language.GEORGIAN: "ნასყიდობის ხელშეკრულება საჯარო რეესტრში რეგისტრირებული არ არის; "
        "მყიდველის უფლება არ არის აღრიცხული.",
        Language.ENGLISH: "The purchase agreement is not registered in the public registry "
        "(NAPR); the buyer's right is not recorded.",
    },
    ReasonCode.LTV_ABOVE_LIMIT: {
        Language.GEORGIAN: "LTV {ltv}% აჭარბებს სებ-ის {limit}%-იან ლიმიტს; "
        "სესხის მაქსიმალური ოდენობაა {max_loan} {currency}.",
        Language.ENGLISH: "LTV {ltv}% exceeds the NBG limit of {limit}%; "
        "the maximum loan is {max_loan} {currency}.",
    },
    ReasonCode.LTV_ABOVE_LIMIT_UNDER_FX_STRESS: {
        Language.GEORGIAN: "ლარის {stress}%-ით გამყარებისას LTV {ltv}%-მდე გაიზრდება "
        "და {limit}%-იან ლიმიტს გადააჭარბებს.",
        Language.ENGLISH: "If the lari strengthens by {stress}%, LTV rises to {ltv}%, "
        "above the {limit}% limit.",
    },
}


def reason_text(flag: Flag, language: Language) -> str:
    params = dict(flag.params)
    for key in ("declared", "observed"):
        if params.get(key):
            params[key] = CONDITION_NAMES[Condition(params[key])][language]
    if params.get("stage"):
        params["stage"] = CONSTRUCTION_STAGE_NAMES[ConstructionStage(params["stage"])][language]
    return REASON_TEMPLATES[flag.code][language].format(**params)


REPORT_ISSUE_TEMPLATES: dict[ReportIssue, Bilingual] = {
    ReportIssue.NO_SITE_INSPECTION: {
        Language.GEORGIAN: "ობიექტის ადგილზე დათვალიერება არ ჩატარებულა.",
        Language.ENGLISH: "The property was not inspected on site.",
    },
    ReportIssue.MISSING_PHOTOS: {
        Language.GEORGIAN: "ანგარიშს არ ახლავს ობიექტის გარე და შიდა ფოტოები.",
        Language.ENGLISH: "Exterior and interior photos are missing.",
    },
    ReportIssue.TOO_FEW_COMPARABLES: {
        Language.GEORGIAN: "გამოყენებულია {count} ანალოგი; საჭიროა მინიმუმ {required}.",
        Language.ENGLISH: "{count} comparables used; at least {required} are required.",
    },
    ReportIssue.SINGLE_ADJUSTMENT_ABOVE_LIMIT: {
        Language.GEORGIAN: "ანალოგი {sale_id}: კორექტირება „{factor}“ {adjustment}%-ია, "
        "ლიმიტი ±{limit}%.",
        Language.ENGLISH: "Comparable {sale_id}: adjustment '{factor}' is {adjustment}%, "
        "the limit is ±{limit}%.",
    },
    ReportIssue.GROSS_ADJUSTMENT_ABOVE_LIMIT: {
        Language.GEORGIAN: "ანალოგი {sale_id}: ჯამური კორექტირება {gross}%-ია და აღემატება "
        "დასაბუთებით დასაშვებ ±{limit}%-ს.",
        Language.ENGLISH: "Comparable {sale_id}: gross adjustment {gross}% exceeds even the "
        "justified limit of ±{limit}%.",
    },
    ReportIssue.GROSS_ADJUSTMENT_UNJUSTIFIED: {
        Language.GEORGIAN: "ანალოგი {sale_id}: ჯამური კორექტირება {gross}% აღემატება ±{limit}%-ს "
        "წერილობითი დასაბუთების გარეშე.",
        Language.ENGLISH: "Comparable {sale_id}: gross adjustment {gross}% is above ±{limit}% "
        "without a written justification.",
    },
    ReportIssue.RESULTS_AVERAGED: {
        Language.GEORGIAN: "სხვადასხვა მეთოდის შედეგები გასაშუალოებულია, რაც დაუშვებელია.",
        Language.ENGLISH: "Results of different approaches were averaged, which is not allowed.",
    },
    ReportIssue.FEWER_APPROACHES_FOR_COMPLEX_PROPERTY: {
        Language.GEORGIAN: "რთული კომერციული ქონებისთვის რეკომენდებულია სამივე მეთოდი; "
        "გამოყენებულია {count}.",
        Language.ENGLISH: "All three approaches are recommended for complex commercial "
        "property; {count} used.",
    },
    ReportIssue.REPORT_CONTENT_MISSING: {
        Language.GEORGIAN: "ანგარიშს აკლია სავალდებულო ნაწილები: {items}.",
        Language.ENGLISH: "The report lacks required parts: {items}.",
    },
}


REPORT_PART_NAMES: dict[str, Bilingual] = {
    "registry_extract": {
        Language.GEORGIAN: "საჯარო რეესტრის ამონაწერი",
        Language.ENGLISH: "registry extract",
    },
    "valuer_signature": {
        Language.GEORGIAN: "შემფასებლის ხელმოწერა",
        Language.ENGLISH: "valuer signature",
    },
    "assumptions": {
        Language.GEORGIAN: "დაშვებები და შეზღუდვები",
        Language.ENGLISH: "assumptions and limitations",
    },
}


def report_finding_text(finding: ReportFinding, language: Language) -> str:
    params = dict(finding.params)
    if "items" in params:
        parts = params["items"].split(", ")
        params["items"] = ", ".join(REPORT_PART_NAMES[part][language] for part in parts)
    return REPORT_ISSUE_TEMPLATES[finding.issue][language].format(**params)
