"""Labels of the officer console in Georgian and English."""

from collateral_engine.i18n import Bilingual, Language

KA, EN = Language.GEORGIAN, Language.ENGLISH

UI_TEXT: dict[str, Bilingual] = {
    "app_title": {KA: "გირაოს შეფასება: მეორე აზრი", EN: "Collateral second opinion"},
    "app_subtitle": {
        KA: "თბილისის ბინები და კერძო სახლები სესხის უზრუნველყოფად · სებ-ის LTV შემოწმება · "
        "გადაწყვეტილებას იღებს საკრედიტო ოფიცერი",
        EN: "Tbilisi flats and houses offered as loan collateral · NBG LTV check · "
        "the loan officer decides",
    },
    "synthetic_notice": {
        KA: "ყველა მონაცემი სინთეტიკურია: არც ერთი რეალური პირი, ბინა, შემფასებელი ან გარიგება.",
        EN: "All data is synthetic: no real person, flat, valuer or transaction.",
    },
    "language": {KA: "ენა", EN: "Language"},
    "demo_case": {KA: "სადემონსტრაციო განაცხადი", EN: "Demo application"},
    "application_section": {KA: "განაცხადი", EN: "Application"},
    "application_id": {KA: "განაცხადის ID", EN: "Application ID"},
    "cadastral_code": {KA: "საკადასტრო კოდი (საჯარო რეესტრი)", EN: "Cadastral code (NAPR)"},
    "district": {KA: "რაიონი", EN: "District"},
    "latitude": {KA: "განედი", EN: "Latitude"},
    "longitude": {KA: "გრძედი", EN: "Longitude"},
    "property_kind": {KA: "ობიექტის ტიპი", EN: "Property type"},
    "house_hint": {
        KA: "კერძო სახლისთვის: კადასტრული კოდი ნაკვეთის კოდია, სართული 1-ია, სართულიანობა კი "
        "სახლის სართულების რაოდენობაა.",
        EN: "For a house: the cadastral code is the parcel code, the floor is 1 and Floors is "
        "the number of storeys.",
    },
    "land_area": {KA: "მიწის ნაკვეთის ფართობი, მ² (სახლი)", EN: "Land plot area, m² (house)"},
    "total_area": {KA: "საერთო ფართი, მ²", EN: "Total area, m²"},
    "rooms": {KA: "ოთახები", EN: "Rooms"},
    "floor": {KA: "სართული", EN: "Floor"},
    "building_floors": {KA: "სართულიანობა", EN: "Floors in the building"},
    "building_status": {KA: "შენობა", EN: "Building"},
    "declared_condition": {KA: "დეკლარირებული მდგომარეობა", EN: "Declared condition"},
    "loan_section": {KA: "სესხი", EN: "Loan"},
    "off_plan_section": {KA: "მშენებარე სახლი", EN: "Building under construction"},
    "off_plan_hint": {
        KA: "ივსება, თუ შენობის სტატუსია „მშენებარე“.",
        EN: "Fill in when the building status is 'Under construction'.",
    },
    "developer_name": {KA: "დეველოპერი", EN: "Developer"},
    "construction_stage": {KA: "მშენებლობის ეტაპი", EN: "Construction stage"},
    "expected_completion_date": {KA: "დასრულების თარიღი", EN: "Expected completion"},
    "agreement_registered": {
        KA: "ნასყიდობის ხელშეკრულება რეგისტრირებულია საჯარო რეესტრში",
        EN: "Purchase agreement registered in the public registry (NAPR)",
    },
    "loan_amount": {KA: "სესხის თანხა", EN: "Loan amount"},
    "loan_currency": {KA: "სესხის ვალუტა", EN: "Loan currency"},
    "has_appraisal": {
        KA: "თან ერთვის ლიცენზირებული შემფასებლის დასკვნა",
        EN: "Licensed appraisal attached",
    },
    "appraised_value": {KA: "შეფასებული საბაზრო ღირებულება", EN: "Appraised market value"},
    "appraisal_currency": {KA: "შეფასების ვალუტა", EN: "Appraisal currency"},
    "photos": {
        KA: "ობიექტის ფოტოები — მინიმუმ {count}, სხვადასხვა ოთახი",
        EN: "Photos of the property — at least {count}, different rooms",
    },
    "photos_help": {
        KA: "JPEG, PNG ან WEBP. გადაიღეთ თავად ობიექტი: კედლები, იატაკი, სამზარეულო, აბაზანა. "
        "კადრში ადამიანები არ უნდა იყვნენ.",
        EN: "JPEG, PNG or WEBP. Photograph the property itself: walls, floors, kitchen, bathroom. "
        "No people in the frame.",
    },
    "photos_count": {KA: "ფოტოები", EN: "Photos"},
    "valuation_date": {KA: "შეფასების თარიღი", EN: "Valuation date"},
    "usd_rate": {KA: "USD/GEL, სებ-ის ოფიციალური კურსი", EN: "USD/GEL, NBG official rate"},
    "fetch_rate": {KA: "სებ-ის კურსის მიღება", EN: "Get the NBG rate"},
    "rate_from_nbg": {KA: "წყარო: სებ, {date}", EN: "Source: NBG, {date}"},
    "rate_manual": {KA: "წყარო: შეიყვანა ოფიცერმა", EN: "Source: entered by the officer"},
    "rate_unavailable": {
        KA: "სებ-ის კურსი მიუწვდომელია ({error}). შეიყვანეთ ხელით.",
        EN: "NBG rate unavailable ({error}). Enter it manually.",
    },
    "assess": {KA: "გირაოს შეფასება", EN: "Assess the collateral"},
    "assessing": {KA: "მიმდინარეობს ობიექტის შეფასება…", EN: "Valuing the property…"},
    "invalid_input": {KA: "შეამოწმეთ განაცხადი: {error}", EN: "Check the application: {error}"},
    "invalid_number": {
        KA: "თანხა და კურსი უნდა იყოს რიცხვი, მაგალითად 220000 ან 2.5976.",
        EN: "Amounts and the rate must be numbers, for example 220000 or 2.5976.",
    },
    "start_hint": {
        KA: "აირჩიეთ სადემონსტრაციო განაცხადი ან შეიყვანეთ საკუთარი და დააჭირეთ "
        "„გირაოს შეფასებას“.",
        EN: "Choose a demo application or enter your own, then press “Assess the collateral”.",
    },
    "recommendation": {KA: "რეკომენდაცია", EN: "Recommendation"},
    "no_reasons": {KA: "პრობლემები არ გამოვლენილა.", EN: "No issues found."},
    "market_value": {KA: "საბაზრო ღირებულება", EN: "Market value"},
    "value_range": {KA: "დიაპაზონი ({coverage}%)", EN: "Range ({coverage}% of sales)"},
    "price_per_m2": {KA: "1 მ²-ის ფასი", EN: "Price per m²"},
    "value_in_gel": {KA: "ლარში, სებ-ის კურსით", EN: "In GEL at the NBG rate"},
    "ltv": {KA: "LTV / სებ-ის ლიმიტი", EN: "LTV / NBG limit"},
    "max_loan": {KA: "მაქსიმალური სესხი LTV-ით", EN: "Maximum loan under LTV"},
    "no_valuation": {
        KA: "შეფასება ვერ მოხერხდა: ახლოს ანალოგიური გაყიდვები არასაკმარისია.",
        EN: "No valuation: too few comparable sales nearby.",
    },
    "range_chart_title": {
        KA: "მოდელის დიაპაზონი და ლიცენზირებული შეფასება",
        EN: "Model range and licensed appraisal",
    },
    "model_estimate": {KA: "მოდელი", EN: "Model"},
    "appraisal": {KA: "შემფასებელი", EN: "Appraiser"},
    "map_title": {
        KA: "ობიექტი, ანალოგიური გაყიდვები და მეტრო",
        EN: "Property, comparable sales, metro",
    },
    "condition_title": {KA: "მდგომარეობა ფოტოების მიხედვით", EN: "Condition from photos"},
    "declared": {KA: "დეკლარირებული", EN: "Declared"},
    "observed": {KA: "ფოტოებზე ჩანს", EN: "Seen in photos"},
    "valued_as": {KA: "შეფასდა როგორც", EN: "Valued as"},
    "not_settled": {KA: "ვერ დადგინდა", EN: "not settled"},
    "photo_ok": {KA: "ხარისხი კარგია", EN: "Quality OK"},
    "vision_off": {KA: "ვიზუალური მოდელი გამორთულია", EN: "Vision model is off"},
    "vision_failed": {KA: "ვერ შეფასდა: {failure}", EN: "Not assessed: {failure}"},
    "seen_elsewhere": {KA: "ასევე განაცხადში: {applications}", EN: "Also in: {applications}"},
    "comparables_title": {
        KA: "კორექტირების ცხრილი (ანალოგიური გაყიდვები)",
        EN: "Adjustment grid (comparable sales)",
    },
    "comparables_caption": {
        KA: "თითოეული გაყიდვის 1 მ²-ის ფასი კორექტირდება ამ ობიექტისთვის; ნაკლები კორექტირების "
        "მქონე გაყიდვებს მეტი წონა აქვს.",
        EN: "Each sale's price per m² is adjusted to this property; sales that need fewer "
        "adjustments weigh more.",
    },
    "column_sale": {KA: "გაყიდვა", EN: "Sale"},
    "column_distance": {KA: "მანძილი, კმ", EN: "Distance, km"},
    "column_date": {KA: "თარიღი", EN: "Date"},
    "column_area": {KA: "ფართი, მ²", EN: "Area, m²"},
    "column_condition": {KA: "მდგომარეობა", EN: "Condition"},
    "column_price": {KA: "1 მ², USD", EN: "Per m², USD"},
    "column_time": {KA: "დრო", EN: "Time"},
    "column_location": {KA: "მდებარეობა", EN: "Location"},
    "column_condition_adjustment": {KA: "მდგომ.", EN: "Condition"},
    "column_building": {KA: "შენობა", EN: "Building"},
    "column_floor": {KA: "სართული", EN: "Floor"},
    "column_size": {KA: "ზომა", EN: "Size"},
    "column_land": {KA: "ნაკვეთი", EN: "Land"},
    "column_land_area": {KA: "ნაკვეთი, მ²", EN: "Land, m²"},
    "column_adjusted": {KA: "კორექტ. 1 მ², USD", EN: "Adjusted per m², USD"},
    "column_weight": {KA: "წონა", EN: "Weight"},
    "column_gross": {KA: "ჯამური კორექტ.", EN: "Gross adjustment"},
    "adjustment_limits": {
        KA: "სებ-ის №84/04, მუხ. 4(5): მინიმუმ {count} ანალოგი; ერთი კორექტირება ≤ ±{single}%, "
        "ჯამური ≤ ±{gross}% (დასაბუთებით ≤ ±{justified}%). ლიმიტს გადაცილებული ანალოგები "
        "არ გამოიყენება.",
        EN: "NBG Order 84/04 Art. 4(5): at least {count} comparables; each adjustment within "
        "±{single}%, gross within ±{gross}% (±{justified}% with justification). Sales beyond the "
        "limits are not used.",
    },
    "income_from_abroad": {
        KA: "მსესხებლის შემოსავალი საზღვარგარეთიდანაა",
        EN: "Borrower's income comes from abroad",
    },
    "ltv_title": {KA: "სებ-ის LTV შემოწმება", EN: "NBG LTV check"},
    "lending_value": {KA: "დაკრედიტების ღირებულება", EN: "Lending value"},
    "basis": {KA: "საფუძველი", EN: "Basis"},
    "rules_version": {KA: "სებ-ის წესების ვერსია", EN: "NBG rules version"},
    "stressed_ltv": {
        KA: "LTV ლარის {stress}%-ით გამყარებისას",
        EN: "LTV if the lari strengthens {stress}%",
    },
    "appraisal_check": {KA: "შემფასებლის დასკვნა", EN: "Licensed appraisal"},
    "decision_title": {KA: "ოფიცრის გადაწყვეტილება", EN: "Officer decision"},
    "officer_id": {KA: "ოფიცრის ID", EN: "Officer ID"},
    "decision": {KA: "გადაწყვეტილება", EN: "Decision"},
    "decision_accept": {KA: "შეფასების მიღება", EN: "Accept the valuation"},
    "decision_inspect": {KA: "ადგილზე დათვალიერების დანიშვნა", EN: "Order a physical inspection"},
    "reason": {
        KA: "მიზეზი (სავალდებულოა, თუ გადაწყვეტილება რეკომენდაციას არ ემთხვევა)",
        EN: "Reason (required when deciding against the recommendation)",
    },
    "record_decision": {KA: "გადაწყვეტილების დაფიქსირება", EN: "Record the decision"},
    "decision_recorded": {
        KA: "ჩაიწერა აუდიტის ჟურნალში, ჰეში {hash}",
        EN: "Recorded in the audit log, hash {hash}",
    },
    "reason_required": {
        KA: "მიუთითეთ მიზეზი: გადაწყვეტილება რეკომენდაციას არ ემთხვევა.",
        EN: "Write a reason: the decision differs from the recommendation.",
    },
    "provenance_title": {KA: "მონაცემები, მოდელი და ვერსიები", EN: "Data, model and versions"},
    "download_report": {KA: "ანგარიშის ჩამოტვირთვა (JSON)", EN: "Download the report (JSON)"},
    "tab_valuation": {KA: "შეფასება", EN: "Valuation"},
    "tab_quality": {KA: "მოდელის ხარისხი", EN: "Model quality"},
    "tab_audit": {KA: "აუდიტის ჟურნალი", EN: "Audit log"},
    "tab_report_check": {KA: "შემფასებლის ანგარიში", EN: "Valuer report check"},
    "report_check_intro": {
        KA: "ქარხნის, სასტუმროს ან ოფისის შეფასებას ასრულებს ლიცენზირებული შემფასებელი; "
        "სისტემა ამოწმებს მის ანგარიშს სებ-ის №84/04 ბრძანების მიხედვით (მუხ. 1(9)).",
        EN: "Factories, hotels and offices are valued by a licensed valuer; the platform checks "
        "the report against NBG Order 84/04, the quality-monitoring role of Art. 1(9).",
    },
    "report_json": {KA: "ანგარიში (JSON)", EN: "Report (JSON)"},
    "report_check_button": {KA: "ანგარიშის შემოწმება", EN: "Check the report"},
    "report_check_ok": {
        KA: "დარღვევები არ გამოვლენილა.",
        EN: "No breaches of NBG Order 84/04 found.",
    },
    "report_check_invalid": {
        KA: "ანგარიში ვერ წაიკითხა: {error}",
        EN: "Cannot read the report: {error}",
    },
    "article": {KA: "სებ-ის №84/04, მუხ. {article}", EN: "NBG Order 84/04, Art. {article}"},
    "recommended": {KA: "რეკომენდაცია", EN: "Recommendation"},
    "required": {KA: "დარღვევა", EN: "Breach"},
    "quality_intro": {
        KA: "დროში გადანაცვლებული ტესტი: ყოველი ბოლოდროინდელი გაყიდვა ფასდება მხოლოდ მანამდე "
        "განხორციელებული გაყიდვებით. სინთეტიკური მონაცემები ამოწმებს მეთოდს "
        "და არა რეალურ სიზუსტეს.",
        EN: "Out-of-time backtest: each recent sale is valued from earlier sales only. "
        "Synthetic data checks the method, not real-world accuracy.",
    },
    "quality_running": {KA: "მიმდინარეობს ტესტი…", EN: "Running the backtest…"},
    "mdape": {KA: "მედიანური ცდომილება", EN: "Median error"},
    "within_10": {KA: "±10%-ის ფარგლებში", EN: "Within ±10%"},
    "within_20": {KA: "±20%-ის ფარგლებში", EN: "Within ±20%"},
    "coverage": {
        KA: "დიაპაზონის დაფარვა (მიზანი {target}%)",
        EN: "Range coverage (target {target}%)",
    },
    "cod": {KA: "COD (IAAO ≤ 15)", EN: "COD (IAAO ≤ 15)"},
    "prd": {KA: "PRD (IAAO 0.98–1.03)", EN: "PRD (IAAO 0.98–1.03)"},
    "sales_tested": {KA: "შემოწმებული გაყიდვები", EN: "Sales tested"},
    "error_by_district": {
        KA: "მედიანური ცდომილება რაიონების მიხედვით",
        EN: "Median error by district",
    },
    "limitations_title": {KA: "ცნობილი შეზღუდვები", EN: "Known limitations"},
    "limitations": {
        KA: "- გაყიდვები სინთეტიკურია; რეალური სიზუსტე ცნობილი იქნება საჯარო რეესტრის მონაცემებზე "
        "საპილოტე ტესტის შემდეგ.\n"
        "- განცხადებების ფასი გარიგების ფასს არ უდრის; რეალურ მონაცემებზე საჭიროა კალიბრაცია.\n"
        "- ფოტოებიდან მდგომარეობის დადგენა არ არის შემოწმებული მონიშნულ ფოტოებზე.\n"
        "- მოდელი აფასებს თბილისის ბინებსა და კერძო სახლებს; მიწის ნაკვეთი შენობის გარეშე მხოლოდ "
        "შემფასებლის ანგარიშის შემოწმებას გადის, რადგან მიწის ფასების ოფიციალური სტატისტიკა "
        "არ არსებობს.\n"
        "- სახლების ფასების საყრდენია Geostat-ის ახალი სახლების შეთავაზების ფასები "
        "(2026 წლის I კვარტალი).",
        EN: "- Sales are synthetic; real accuracy is known only after a pilot on public registry "
        "data.\n"
        "- Asking prices differ from transaction prices; calibrate on real deals.\n"
        "- The condition reading from photos has not been measured on labelled photos yet.\n"
        "- The model values flats and private houses in Tbilisi; land without a building gets the "
        "valuer report check only, because there is no official land price series.\n"
        "- House prices are anchored to Geostat offer prices for new houses (Q1 2026).",
    },
    "audit_verify": {KA: "ჰეშ-ჯაჭვის შემოწმება", EN: "Verify the hash chain"},
    "audit_intact": {
        KA: "ჯაჭვი მთლიანია: შემოწმდა {count} ჩანაწერი.",
        EN: "Chain intact: {count} records checked.",
    },
    "audit_broken": {
        KA: "ჯაჭვი დარღვეულია: ჩანაწერი შეიცვალა ან წაიშალა.",
        EN: "Chain broken: a record was changed or deleted.",
    },
    "audit_empty": {KA: "ჩანაწერები ჯერ არ არის.", EN: "No records yet."},
    "tab_vehicle": {KA: "ავტომობილი", EN: "Vehicle"},
    "full_title": {KA: "სრული განაცხადი", EN: "Full loan application"},
    "full_intro": {
        KA: "ერთი განაცხადი: შემოსავალი Open Banking-ის ტრანზაქციებიდან (სებ-ის PTI) და "
        "გირაო (LTV). შეთავაზება ორივე ლიმიტს აკმაყოფილებს; გადაწყვეტილებას იღებს ოფიცერი.",
        EN: "One application: income from consented Open Banking transactions (NBG PTI) and "
        "the collateral (LTV). The offer meets both limits; the loan officer decides.",
    },
    "borrower": {KA: "მსესხებელი (სინთეტიკური)", EN: "Borrower (synthetic)"},
    "collateral_kind": {KA: "გირაო", EN: "Collateral"},
    "real_estate": {KA: "უძრავი ქონება", EN: "Real estate"},
    "vehicle": {KA: "ავტომობილი", EN: "Vehicle"},
    "collateral_case": {KA: "გირაოს ნიმუში", EN: "Collateral case"},
    "full_photos": {KA: "გირაოს ფოტოები", EN: "Collateral photos"},
    "assess_full": {KA: "განაცხადის შეფასება", EN: "Assess the application"},
    "full_start_hint": {
        KA: "აირჩიეთ მსესხებელი და გირაო, შემდეგ დააჭირეთ „განაცხადის შეფასებას“.",
        EN: "Pick a borrower and a collateral, then press 'Assess the application'.",
    },
    "full_loan_note": {
        KA: "სესხი: {amount} ლარი, {term} თვე — მსესხებლის განაცხადიდან; გირაოს შეფასება იმავე "
        "სესხისთვის კეთდება.",
        EN: "Loan: {amount} GEL over {term} months, from the borrower's application; the "
        "collateral is assessed for the same loan.",
    },
    "requested_amount": {KA: "მოთხოვნილი", EN: "Requested"},
    "max_by_income": {KA: "მაქსიმუმი შემოსავლით (PTI)", EN: "Maximum by income (PTI)"},
    "max_by_collateral": {KA: "მაქსიმუმი გირაოთი (LTV)", EN: "Maximum by collateral (LTV)"},
    "offer_amount": {KA: "შეთავაზება", EN: "Offer"},
    "binding_limit": {KA: "შემზღუდველი ლიმიტი: {limit}", EN: "Binding limit: {limit}"},
    "income_section": {KA: "შემოსავალი", EN: "Income"},
    "income_recommendation": {KA: "შემოსავლის შეფასება", EN: "Income assessment"},
    "income_band": {KA: "თვიური შემოსავალი P10–P90", EN: "Monthly income P10–P90"},
    "income_conservative": {
        KA: "PTI-სთვის: P25 = {amount} ლარი",
        EN: "For PTI: P25 = {amount} GEL",
    },
    "pti": {KA: "PTI / ლიმიტი", EN: "PTI / limit"},
    "default_probability": {KA: "დეფოლტის ალბათობა (12 თვე)", EN: "Default probability (12 m)"},
    "income_flags": {KA: "შენიშვნები", EN: "Notes"},
    "income_reasons": {KA: "მთავარი ფაქტორები", EN: "Main factors"},
    "collateral_section": {KA: "გირაო", EN: "Collateral"},
    "income_unavailable": {
        KA: "შემოსავლის მოდელი არ არის მზად: {error}",
        EN: "The income model is not ready: {error}",
    },
    "vehicle_intro": {
        KA: "ავტომობილი სესხის უზრუნველყოფად. სებ-ის №84/04 ბრძანება მხოლოდ უძრავ ქონებას "
        "ეხება და სებ ავტოსესხზე LTV ლიმიტს არ ადგენს, ამიტომ ლიმიტი და ვადა ბანკის "
        "პოლიტიკიდანაა.",
        EN: "A vehicle offered as loan collateral. NBG Order 84/04 covers real estate only and "
        "NBG sets no LTV limit for vehicle loans, so the limit and term come from bank policy.",
    },
    "vehicle_demo_case": {KA: "სადემონსტრაციო განაცხადი", EN: "Demo application"},
    "vin": {KA: "VIN კოდი", EN: "VIN"},
    "plate_number": {KA: "სახელმწიფო ნომერი", EN: "Registration plate"},
    "make": {KA: "მარკა", EN: "Make"},
    "model": {KA: "მოდელი", EN: "Model"},
    "production_year": {KA: "გამოშვების წელი", EN: "Production year"},
    "mileage": {KA: "გარბენი, კმ", EN: "Mileage, km"},
    "engine_volume": {KA: "ძრავის მოცულობა, სმ³", EN: "Engine volume, cm³"},
    "fuel": {KA: "საწვავი", EN: "Fuel"},
    "steering": {KA: "საჭე", EN: "Steering"},
    "customs_cleared": {KA: "განბაჟებულია", EN: "Cleared through customs"},
    "accident_history": {KA: "ავარიის ისტორია", EN: "Accident history"},
    "loan_term": {KA: "სესხის ვადა, თვე", EN: "Loan term, months"},
    "vehicle_photos": {
        KA: "ავტომობილის ფოტოები — მინიმუმ {count}: წინა, უკანა, ორივე გვერდი, ოდომეტრი, VIN",
        EN: "Vehicle photos — at least {count}: front, rear, both sides, odometer, VIN plate",
    },
    "assess_vehicle": {KA: "ავტომობილის შეფასება", EN: "Value the vehicle"},
    "vehicle_start_hint": {
        KA: "აირჩიეთ განაცხადი ან შეავსეთ ფორმა და დააჭირეთ „ავტომობილის შეფასებას“.",
        EN: "Pick an application or fill in the form and press 'Value the vehicle'.",
    },
    "vehicle_value": {KA: "საბაზრო ღირებულება", EN: "Market value"},
    "projected_value": {
        KA: "ღირებულება სესხის ბოლოს ({months} თვე)",
        EN: "Value at the end of the loan ({months} months)",
    },
    "annual_depreciation": {KA: "წლიური ცვეთა", EN: "Depreciation per year"},
    "age_at_maturity": {KA: "ასაკი სესხის ბოლოს", EN: "Age when the loan ends"},
    "years": {KA: "{count} წელი", EN: "{count} years"},
    "bank_ltv_title": {KA: "LTV ბანკის პოლიტიკით", EN: "LTV under bank policy"},
    "vehicle_comparables_caption": {
        KA: "იმავე მარკისა და მოდელის გაყიდვები; ფასი კორექტირდება ამ ავტომობილისთვის, "
        "ნაკლები კორექტირების მქონე გაყიდვებს მეტი წონა აქვს.",
        EN: "Sales of the same make and model, each adjusted to this vehicle; sales that need "
        "fewer adjustments weigh more.",
    },
    "column_year": {KA: "წელი", EN: "Year"},
    "column_mileage": {KA: "გარბენი, კმ", EN: "Mileage, km"},
    "column_price_usd": {KA: "ფასი, USD", EN: "Price, USD"},
    "column_adjusted_usd": {KA: "კორექტ. ფასი, USD", EN: "Adjusted price, USD"},
    "vehicle_photo_count": {
        KA: "ფოტოები: {count} / {required}",
        EN: "Photos: {count} of {required}",
    },
}
