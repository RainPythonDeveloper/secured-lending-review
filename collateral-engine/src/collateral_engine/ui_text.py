"""Labels of the officer console in Georgian and English."""

from collateral_engine.i18n import Bilingual, Language

KA, EN = Language.GEORGIAN, Language.ENGLISH

UI_TEXT: dict[str, Bilingual] = {
    "language": {KA: "ენა", EN: "Language"},
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
    "off_plan_section": {KA: "მშენებარე სახლი", EN: "Building under construction"},
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
    "photos_count": {KA: "ფოტოები", EN: "Photos"},
    "valuation_date": {KA: "შეფასების თარიღი", EN: "Valuation date"},
    "usd_rate": {KA: "USD/GEL, სებ-ის ოფიციალური კურსი", EN: "USD/GEL, NBG official rate"},
    "invalid_input": {KA: "შეამოწმეთ განაცხადი: {error}", EN: "Check the application: {error}"},
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
    "observed": {KA: "AI ხედავს ფოტოებზე", EN: "AI sees in the photos"},
    "valued_as": {KA: "შეფასდა როგორც", EN: "Valued as"},
    "not_settled": {KA: "ვერ დადგინდა", EN: "Not settled"},
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
    "officer_id": {KA: "ოფიცრის ID", EN: "Officer ID"},
    "decision": {KA: "გადაწყვეტილება", EN: "Decision"},
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
    "audit_verify": {KA: "ჰეშ-ჯაჭვის შემოწმება", EN: "Verify the hash chain"},
    "audit_intact": {
        KA: "ჯაჭვი მთლიანია: შემოწმდა {count} ჩანაწერი.",
        EN: "Chain intact: {count} records checked.",
    },
    "audit_broken": {
        KA: "ჯაჭვი დარღვეულია: ჩანაწერი შეიცვალა ან წაიშალა.",
        EN: "Chain broken: a record was changed or deleted.",
    },
    "loan_title": {KA: "სესხის განაცხადი", EN: "Loan application"},
    "loan_lead": {
        KA: "ერთი პროცესი: განმცხადებელი → დისტანციური იდენტიფიკაცია → სესხი → ავტომატური "
        "შემოწმებები → ოფიცრის გადაწყვეტილება. ყველა მონაცემი სინთეტიკურია.",
        EN: "One pipeline: applicant → remote identification → loan → automated checks → the "
        "officer's decision. All data is synthetic.",
    },
    "step_applicant": {KA: "1 · განმცხადებელი", EN: "1 · Applicant"},
    "step_identification": {
        KA: "2 · დისტანციური იდენტიფიკაცია",
        EN: "2 · Remote identification",
    },
    "step_loan": {KA: "3 · სესხი", EN: "3 · Loan"},
    "step_checks": {KA: "4 · შემოწმებები", EN: "4 · Checks"},
    "liveness_title": {
        KA: "ცოცხალი პირის შემოწმება · სებ-ის ბრძანება 104/04",
        EN: "Liveness check · NBG Order 104/04",
    },
    "liveness_note": {
        KA: "{count} შემთხვევითი დავალება კამერის წინ. სახის წერტილების მოდელი ამ ბრაუზერში "
        "ადევნებს თვალს თავისა და თვალების მოძრაობას; სტატუსს ბანკის წესები ადგენს.",
        EN: "{count} randomly chosen tasks in front of the camera. A face landmark model follows "
        "the head and eye movements in this browser; the bank's rules set the status.",
    },
    "liveness_skip_hint": {
        KA: "გამოტოვეთ ეს ნაბიჯი, თუ განმცხადებელი ფილიალში პირადად იდენტიფიცირდება.",
        EN: "Skip this step when the applicant is identified in person in a branch.",
    },
    "liveness_need_data": {
        KA: "ჯერ ჩატვირთეთ განმცხადებლის მონაცემები.",
        EN: "Load the applicant's data first.",
    },
    "liveness_too_young": {
        KA: "განმცხადებელი {age} წლამდეა: არასრულწლოვნებს არ ვიღებთ; იდენტიფიკაცია ფილიალში.",
        EN: "The applicant is under {age}: minors are not filmed; identify them in a branch.",
    },
    "liveness_attempt": {
        KA: "მცდელობა {attempt} / {max} ბოლო 24 საათში",
        EN: "Attempt {attempt} of {max} in the last 24 hours",
    },
    "liveness_attempts_used": {
        KA: "ბოლო 24 საათის {max} მცდელობა ამოიწურა (სებ-ის ბრძანება 104/04): განმცხადებელი "
        "ფილიალში იდენტიფიცირდება.",
        EN: "All {max} attempts of the last 24 hours are used (NBG Order 104/04): identify the "
        "applicant in a branch.",
    },
    "liveness_retry": {KA: "ახალი მცდელობა, ახალი დავალებებით", EN: "New attempt, new tasks"},
    "liveness_invalid": {
        KA: "ბრაუზერის სესია წესებს არ შეესაბამება: {error}",
        EN: "The session from the browser does not match the rules: {error}",
    },
    "liveness_tasks_done": {
        KA: "შესრულებულია {completed} დავალება {total}-დან · {frames} კადრი გაანალიზდა",
        EN: "{completed} of {total} tasks done · {frames} frames analysed",
    },
    "liveness_missed": {KA: "დრო ამოიწურა", EN: "Time is up"},
    "liveness_not_stored": {
        KA: "მიღებული კადრები არ ინახება: ისინი მხოლოდ ამ სესიაში ჩანს, აუდიტის ჟურნალში კი "
        "მხოლოდ მათი SHA-256 იწერება.",
        EN: "The captured frames are not stored: they are shown only in this session, and the "
        "audit log keeps nothing but their SHA-256.",
    },
    "tab_identification": {KA: "დისტანციური იდენტიფიკაცია", EN: "Remote identification"},
    "lv_kicker": {
        KA: "სებ 104/04 · დისტანციური იდენტიფიკაცია",
        EN: "NBG 104/04 · remote identification",
    },
    "lv_start_title": {KA: "ცოცხალი პირის შემოწმება", EN: "Liveness check"},
    "lv_start_hint": {
        KA: "განმცხადებელი კამერის წინ ასრულებს {count} შემთხვევით დავალებას.",
        EN: "The applicant performs {count} randomly chosen tasks in front of the camera.",
    },
    "lv_idle": {
        KA: "კამერა ჩაირთვება ღილაკზე დაჭერის შემდეგ.",
        EN: "The camera starts when you press the button.",
    },
    "lv_start_button": {KA: "კამერის ჩართვა", EN: "Start the camera"},
    "lv_loading": {KA: "სახის მოდელი იტვირთება…", EN: "Loading the face model…"},
    "lv_align_title": {KA: "შეხედეთ კამერას", EN: "Look at the camera"},
    "lv_align_hint": {
        KA: "მოათავსეთ სახე ოვალში და გაჩერდით წამით.",
        EN: "Keep your face inside the oval and hold still for a moment.",
    },
    "lv_task_hint": {
        KA: "შეასრულეთ დავალება და დაბრუნდით კამერისკენ.",
        EN: "Do the task, then look back at the camera.",
    },
    "lv_several_people": {
        KA: "კადრში მხოლოდ განმცხადებელი უნდა იყოს",
        EN: "Only the applicant should be in the frame",
    },
    "lv_no_face": {
        KA: "სახე ვერ მოიძებნა — მიუახლოვდით კამერას",
        EN: "No face found — move closer",
    },
    "lv_step": {KA: "დავალება {n} / {total}", EN: "Task {n} of {total}"},
    "lv_task_done": {KA: "შესრულდა", EN: "Done"},
    "lv_done_title": {KA: "სესია დასრულდა", EN: "Session complete"},
    "lv_done_hint": {
        KA: "ბანკის წესები ამოწმებს სესიას…",
        EN: "The bank's rules are checking the session…",
    },
    "lv_privacy": {
        KA: "მუშავდება ამ მოწყობილობაზე. კადრები არ ინახება; აუდიტის ჟურნალში მხოლოდ მათი "
        "SHA-256 იწერება.",
        EN: "Processed on this device. The frames are not stored; only their SHA-256 goes to "
        "the audit log.",
    },
    "lv_model_label": {KA: "მოწყობილობაზე", EN: "On device"},
    "lv_frames_label": {KA: "კადრი", EN: "frames"},
    "lv_people_label": {KA: "ადამიანი კადრში", EN: "people in frame"},
    "path_existing": {KA: "არსებული კლიენტი", EN: "Existing customer"},
    "path_new": {KA: "ახალი კლიენტი", EN: "New customer"},
    "path_existing_hint": {
        KA: "ბანკის კლიენტი NBG-ის სინთეტიკური მონაცემებიდან; ანგარიშები და ტრანზაქციები მოდის "
        "Open Banking API-ით, კლიენტის თანხმობის შემდეგ.",
        EN: "A bank customer from the NBG synthetic dataset; accounts and transactions come "
        "through the Open Banking API after the customer's consent.",
    },
    "path_new_hint": {
        KA: "განმცხადებელი ბანკში ისტორიის გარეშე; მისი 6-თვიანი ამონაწერი სინთეტიკურად იქმნება.",
        EN: "An applicant with no history at the bank; a six-month statement is generated.",
    },
    "customer": {KA: "კლიენტი", EN: "Customer"},
    "profile_age": {KA: "ასაკი", EN: "Age"},
    "profile_city": {KA: "ქალაქი", EN: "City"},
    "profile_type": {KA: "პროფილი", EN: "Profile"},
    "ob_title": {KA: "Open Banking თანხმობა", EN: "Open Banking consent"},
    "ob_request": {KA: "1. თანხმობის მოთხოვნა", EN: "1. Request consent"},
    "ob_approve": {KA: "2. დადასტურება ბანკში ↗", EN: "2. Approve at the bank ↗"},
    "ob_load": {KA: "3. მონაცემების ჩატვირთვა", EN: "3. Load the data"},
    "ob_hint": {
        KA: "TBC sandbox-ის გვერდზე დააჭირეთ „Approve“, შემდეგ დაბრუნდით და ჩატვირთეთ მონაცემები.",
        EN: "On the TBC sandbox page press Approve, then come back and load the data.",
    },
    "ob_consent_created": {KA: "თანხმობა შეიქმნა: {consent}", EN: "Consent created: {consent}"},
    "ob_not_approved": {
        KA: "თანხმობა ჯერ არ არის დადასტურებული ბანკში.",
        EN: "The consent is not approved at the bank yet.",
    },
    "ob_failed": {
        KA: "Open Banking მიუწვდომელია: {error}",
        EN: "Open Banking is not available: {error}",
    },
    "use_bank_records": {KA: "ბანკის ჩანაწერების გამოყენება", EN: "Use the bank's records"},
    "use_bank_records_hint": {
        KA: "სარეზერვო გზა, თუ gateway ან sandbox მიუწვდომელია.",
        EN: "Fallback when the gateway or the sandbox is down.",
    },
    "new_profile": {KA: "პროფილი", EN: "Profile"},
    "new_declared": {KA: "დეკლარირებული შემოსავალი, ლარი", EN: "Declared income, GEL"},
    "new_seed": {KA: "ვარიანტი (seed)", EN: "Variant (seed)"},
    "generate_applicant": {KA: "განმცხადებლის შექმნა", EN: "Generate the applicant"},
    "data_loaded": {
        KA: "{source} · {transactions} ტრანზაქცია · {accounts} ანგარიში · {start} – {end}",
        EN: "{source} · transactions: {transactions} · accounts: {accounts} · {start} – {end}",
    },
    "statement_preview": {KA: "ამონაწერი", EN: "Statement"},
    "loan_product": {KA: "პროდუქტი", EN: "Product"},
    "loan_rate": {KA: "წლიური განაკვეთი, %", EN: "Annual rate, %"},
    "run_checks": {KA: "შემოწმებების გაშვება", EN: "Run the checks"},
    "running_checks": {KA: "მიმდინარეობს შემოწმებები…", EN: "Running the checks…"},
    "need_data": {
        KA: "ჯერ ჩატვირთეთ განმცხადებლის მონაცემები (ნაბიჯი 1).",
        EN: "Load the applicant's data first (step 1).",
    },
    "checks_title": {KA: "ავტომატური შემოწმებები", EN: "Automated checks"},
    "offer_line": {
        KA: "შეთავაზება: {amount} ლარი · {term} თვე · {payment} ლარი თვეში",
        EN: "Offer: {amount} GEL · {term} months · {payment} GEL a month",
    },
    "time_saved": {
        KA: "შემოწმდა {duration}-ში, ხელით შემოწმების დაახლოებით {minutes} წუთის ნაცვლად",
        EN: "Checked in {duration} instead of about {minutes} minutes of manual checks",
    },
    "tab_credit": {KA: "საკრედიტო ისტორია", EN: "Credit history"},
    "income_by_month": {KA: "შემოსავალი თვეების მიხედვით, ლარი", EN: "Income by month, GEL"},
    "income_confirmed_label": {KA: "დადასტურებული", EN: "Confirmed"},
    "income_declared_label": {KA: "დეკლარირებული", EN: "Declared"},
    "income_documented_label": {
        KA: "დოკუმენტირებული (RS.ge, stand-in)",
        EN: "Documented (RS.ge stand-in)",
    },
    "income_for_pti_label": {KA: "PTI-სთვის (P25)", EN: "For PTI (P25)"},
    "credit_score": {KA: "ქულა", EN: "Score"},
    "no_history": {KA: "ისტორია არ არის", EN: "No history"},
    "obligations": {KA: "ვალდებულებები", EN: "Obligations"},
    "worst_dpd": {KA: "მაქს. ვადაგადაცილება, დღე", EN: "Worst days past due"},
    "monthly_payments": {KA: "ყოველთვიური გადასახადები", EN: "Monthly payments"},
    "officer_decision": {KA: "ოფიცრის გადაწყვეტილება", EN: "Officer's decision"},
    "decision_amount": {KA: "თანხა, ლარი", EN: "Amount, GEL"},
    "stage_source": {KA: "წყარო", EN: "Source"},
    "rates_note": {KA: "ვალუტის კურსები: სებ, {date}", EN: "Exchange rates: NBG, {date}"},
    "rates_missing": {
        KA: "{currencies}: სებ-ის კურსი ვერ მივიღეთ — ამ ვალუტით შემოსავალი არ ითვლება.",
        EN: "No NBG rate for {currencies}; income in it is not counted.",
    },
    "loan_start_hint": {
        KA: "აირჩიეთ განმცხადებელი, ჩატვირთეთ მისი მონაცემები, შეავსეთ სესხი და გაუშვით "
        "შემოწმებები.",
        EN: "Pick an applicant, load their data, fill in the loan and run the checks.",
    },
    "product_name": {KA: "უზრუნველყოფილი სესხის შეფასება", EN: "Secured Lending Review"},
    "product_lead": {
        KA: "ერთი სესხის განაცხადი, რომელიც ასრულებს ოფიცრის წინასასესხო შემოწმებებს: პირი და "
        "სიები, საკრედიტო ისტორია, შემოსავალი Open Banking-იდან, სებ-ის ლიმიტები და გირაოს "
        "დამოუკიდებელი შეფასება. გადაწყვეტილებას ადამიანი იღებს.",
        EN: "One loan application that runs the officer's pre-loan checks: identity and "
        "watchlists, credit history, income from Open Banking, the NBG limits and an independent "
        "valuation of the collateral. A person makes the decision.",
    },
    "chip_open_banking": {KA: "Open Banking (Berlin Group)", EN: "Open Banking (Berlin Group)"},
    "chip_pti_ltv": {KA: "სებ-ის PTI და LTV", EN: "NBG PTI and LTV"},
    "chip_84_04": {KA: "სებ-ის №84/04 ბრძანება", EN: "NBG Order 84/04"},
    "chip_audit": {KA: "ჰეშ-ჯაჭვიანი აუდიტი", EN: "Hash-chained audit"},
    "chip_synthetic": {KA: "მხოლოდ სინთეტიკური მონაცემები", EN: "Synthetic data only"},
    "overview_flow_title": {KA: "როგორ მუშაობს", EN: "How it works"},
    "overview_flow_lead": {
        KA: "ერთი განაცხადი ოთხ ნაბიჯად — ყოველი ციფრი ახსნილია და აუდიტში ჩაწერილი.",
        EN: "One application in four steps; every number is explained and written to the audit.",
    },
    "step1_title": {KA: "განმცხადებელი და მონაცემები", EN: "Applicant and data"},
    "step1_body": {
        KA: "არსებული კლიენტის ანგარიშები მოდის Open Banking-ით თანხმობის შემდეგ ან ბანკის "
        "ჩანაწერებიდან; ახალ კლიენტს აქვს ექვსთვიანი სინთეტიკური ამონაწერი.",
        EN: "An existing customer's accounts come through Open Banking after consent, or from the "
        "bank's records; a new customer brings a synthetic six-month statement.",
    },
    "step1_tag": {KA: "Open Banking · Berlin Group", EN: "Open Banking · Berlin Group"},
    "step2_title": {KA: "პირი, ისტორია, შემოსავალი", EN: "Identity, history, income"},
    "step2_body": {
        KA: "სანქციების სიები და მოვალეთა რეესტრი, საკრედიტო ისტორია და შემოსავალი, "
        "დადასტურებული ამონაწერის სრული თვეებით.",
        EN: "Watchlists and the debtors registry, the credit history, and income confirmed from "
        "whole months of the statement.",
    },
    "step2_tag": {KA: "გამჭვირვალე წესები", EN: "Transparent rules"},
    "step3_title": {KA: "სებ-ის ლიმიტები და გირაო", EN: "NBG limits and collateral"},
    "step3_body": {
        KA: "PTI, ლარში სესხება და მაქსიმალური ვადა სებ-ის თარიღიანი წესებით; ბინა, სახლი ან "
        "ავტომობილი ფასდება ანალოგიური გაყიდვებით და ფოტოებით, LTV კი ზღუდავს შეთავაზებას.",
        EN: "PTI, GEL lending and the longest term follow the dated NBG rules; the flat, house or "
        "car is valued from comparable sales and photos, and LTV caps the offer.",
    },
    "step3_tag": {KA: "სებ-ის წესები · გირაოს მოდელი", EN: "NBG rules · collateral model"},
    "step4_title": {KA: "ოფიცერი წყვეტს", EN: "The officer decides"},
    "step4_body": {
        KA: "შეთავაზება ორივე ლიმიტს აკმაყოფილებს. ავტომატური უარი არ არის; რეკომენდაციისგან "
        "განსხვავებული გადაწყვეტილება მიზეზს მოითხოვს.",
        EN: "The offer meets both limits. There is no automatic refusal; a decision against the "
        "recommendation needs a written reason.",
    },
    "step4_tag": {KA: "ადამიანი წყვეტს", EN: "Human in the loop"},
    "overview_quality_title": {
        KA: "ხარისხი სინთეტიკურ მონაცემებზე",
        EN: "Quality on synthetic data",
    },
    "overview_quality_lead": {
        KA: "დროში გადანაცვლებული ტესტი: ყოველი შემთხვევა ფასდება მხოლოდ წინა მონაცემებით.",
        EN: "Out-of-time tests: every case is assessed from earlier data only.",
    },
    "kpi_income_check": {
        KA: "შემოსავლის შემოწმება, სებ-ის მონაცემები",
        EN: "Income check on NBG data",
    },
    "kpi_income_check_note": {
        KA: "მედიანური ცდომილება, {count} კლიენტი; P90 {p90}",
        EN: "Median error, {count} customers; P90 {p90}",
    },
    "kpi_flat_error": {KA: "ბინის შეფასების ცდომილება", EN: "Flat valuation error"},
    "kpi_house_error": {KA: "სახლის შეფასების ცდომილება", EN: "House valuation error"},
    "kpi_vehicle_error": {KA: "ავტომობილის შეფასების ცდომილება", EN: "Vehicle valuation error"},
    "kpi_error_note": {KA: "მედიანური, {count} გაყიდვა", EN: "Median, {count} sales"},
    "overview_metrics_missing": {
        KA: "მეტრიკები ჯერ არ არის: გაუშვით make data და make evaluate.",
        EN: "No metrics yet: run make data and make evaluate.",
    },
    "overview_guarantees_title": {KA: "პასუხისმგებლიანი AI", EN: "Responsible AI"},
    "g1_title": {KA: "სტატუსს წესები ადგენს", EN: "Rules set every status"},
    "g1_body": {
        KA: "სებ-ის ლიმიტები თარიღიან კონფიგურაციაშია; ენობრივი მოდელის ტექსტი სტატუსს ვერ ცვლის.",
        EN: "NBG limits live in dated configuration; language-model text never sets a status.",
    },
    "g2_title": {KA: "ავტომატური უარი არ არის", EN: "No automatic refusal"},
    "g2_body": {
        KA: "უარესი შედეგია ოფიცრის განხილვა ან ადგილზე დათვალიერება.",
        EN: "The worst outcome is an officer review or a physical inspection.",
    },
    "g3_title": {KA: "ყოველი ნაბიჯი აუდიტშია", EN: "Every step is audited"},
    "g3_body": {
        KA: "ფოტოები SHA-256-ით, შეფასებები და გადაწყვეტილებები ჰეშ-ჯაჭვში.",
        EN: "Photos by SHA-256, assessments and decisions in a hash chain.",
    },
    "g4_title": {KA: "სახიდან არაფერი დგინდება", EN: "Nothing inferred from faces"},
    "g4_body": {
        KA: "ცოცხალი პირის შემოწმება მხოლოდ თავისა და თვალების მოძრაობას ამოწმებს; კადრები არ "
        "ინახება, სახის ნიშნები და დაცული ატრიბუტები მოდელებში არ შედის.",
        EN: "The liveness check follows only head and eye movements; frames are not stored, and "
        "no traits read from faces and no protected attributes go into the models.",
    },
    "overview_try_title": {KA: "სცადეთ", EN: "Try it"},
    "try_full": {KA: "სესხის განაცხადი →", EN: "Loan application →"},
    "profile_declared": {KA: "დეკლარირებული შემოსავალი", EN: "Declared income"},
    "photos_optional": {
        KA: "ფოტოები არასავალდებულოა დემოში; მათ გარეშე მდგომარეობა გადაუმოწმებელია და განაცხადი "
        "განხილვაზე გადადის.",
        EN: "Photos are optional in the demo; without them the condition stays unverified and the "
        "application goes to review.",
    },
    "limits_title": {KA: "რამდენის გაცემაა შესაძლებელი", EN: "How much can be lent"},
    "bar_requested": {KA: "მოთხოვნილი", EN: "Requested"},
    "bar_requested_detail": {KA: "მსესხებლის განაცხადი", EN: "the borrower's application"},
    "bar_income": {KA: "შემოსავლის ლიმიტი (PTI)", EN: "Income limit (PTI)"},
    "bar_income_detail": {
        KA: "სებ, კონსერვატიული შემოსავლით (P25)",
        EN: "NBG, on the conservative income (P25)",
    },
    "bar_collateral": {KA: "გირაოს ლიმიტი (LTV)", EN: "Collateral limit (LTV)"},
    "bar_collateral_detail_real_estate": {
        KA: "სებ-ის LTV, გირაოს ღირებულებით",
        EN: "NBG LTV on the collateral value",
    },
    "bar_collateral_detail_vehicle": {
        KA: "ბანკის პოლიტიკა, ავტომობილის ღირებულებით",
        EN: "Bank policy on the vehicle value",
    },
    "bar_offer": {KA: "შეთავაზება", EN: "Offer"},
    "bar_offer_detail": {KA: "მოთხოვნა, ორივე ლიმიტში", EN: "the request, within both limits"},
    "beyond_scale": {KA: "სკალის მიღმა", EN: "beyond the scale"},
    "tab_income_detail": {KA: "შემოსავალი", EN: "Income"},
    "tab_collateral_detail": {KA: "გირაო", EN: "Collateral"},
    "collateral_title": {KA: "გირაო", EN: "Collateral"},
    "tab_collateral_ai": {KA: "გირაო · AI ანალიზი", EN: "Collateral · AI analysis"},
    "ai_section_title": {KA: "ფოტოების AI ანალიზი", EN: "AI analysis of the photos"},
    "ai_disclaimer": {
        KA: "მოდელი მხოლოდ აღწერს თითოეულ ფოტოს მკაცრი JSON სქემით; სტატუსებს ადგენს "
        "ვერსიული წესები, არა მოდელის ტექსტი.",
        EN: "The model only describes each photo in a strict JSON schema; versioned rules, not "
        "the model's text, set every status.",
    },
    "ai_off": {
        KA: "AI ანალიზი გამორთულია: ჩართეთ COLLATERAL_VISION_ENABLED და მიუთითეთ პროვაიდერის "
        "გასაღები. ფოტოები მაინც მოწმდება და ჰეშით ინახება; სტატუსები INCONCLUSIVE რჩება.",
        EN: "AI analysis is off: set COLLATERAL_VISION_ENABLED and a provider key. Photos are "
        "still checked and hashed; every status stays INCONCLUSIVE.",
    },
    "ai_not_read": {KA: "ვერ წაიკითხა", EN: "Not read"},
    "ai_declared": {KA: "დეკლარირებული", EN: "declared"},
    "ai_damage": {KA: "ძარის დაზიანება", EN: "Body damage"},
    "ai_views": {KA: "ნაპოვნი ხედები", EN: "Views found"},
    "ai_photo_not_counted": {
        KA: "არ ჩაითვალა: დაბალი სანდოობა, ადამიანი კადრში ან ავტომობილი არ ჩანს",
        EN: "Not counted: low confidence, a person in the frame or no vehicle",
    },
    "valuation_section": {KA: "საბაზრო შეფასება და LTV", EN: "Market valuation and LTV"},
    "collateral_title_real_estate": {
        KA: "იპოთეკის უზრუნველყოფა: ბინა ან კერძო სახლი თბილისში.",
        EN: "Security for the mortgage: a flat or a private house in Tbilisi.",
    },
    "collateral_title_vehicle": {
        KA: "ავტოსესხის უზრუნველყოფა: თავად ავტომობილი.",
        EN: "Security for the car loan: the vehicle itself.",
    },
    "collateral_mode": {KA: "გირაოს მონაცემები", EN: "Collateral data"},
    "collateral_mode_demo": {KA: "სადემონსტრაციო შემთხვევა", EN: "Demo case"},
    "collateral_mode_manual": {KA: "თავად შევავსებ", EN: "Fill in myself"},
    "collateral_demo_hint": {
        KA: "ველის შესაცვლელად აირჩიეთ „თავად შევავსებ“: ფორმა ამ შემთხვევით შეივსება.",
        EN: "To change any field, choose 'Fill in myself': the form starts from this case.",
    },
    "collateral_manual_hint": {
        KA: "ფორმა შევსებულია არჩეული სადემონსტრაციო შემთხვევით; შეცვალეთ ის, რაც განსხვავდება.",
        EN: "The form starts from the chosen demo case; change whatever differs.",
    },
    "collateral_not_needed": {
        KA: "სამომხმარებლო სესხი უზრუნველყოფის გარეშეა, ამიტომ გირაო არ ფასდება.",
        EN: "A consumer loan has no collateral, so nothing is valued here.",
    },
    "ltv_bank_limit": {KA: "LTV / ბანკის ლიმიტი", EN: "LTV / bank limit"},
    "floor_of_building": {KA: "სართული / სართულიანობა", EN: "Floor / storeys"},
    "no_appraisal": {KA: "არ არის", EN: "None attached"},
    "yes": {KA: "კი", EN: "Yes"},
    "no": {KA: "არა", EN: "No"},
    "audit_intro": {
        KA: "განაცხადის ყოველი ნაბიჯი იწერება ჰეშ-ჯაჭვით დაცულ ჟურნალში; ჩანაწერი არ იცვლება "
        "და არ იშლება.",
        EN: "Every step of this application is appended to a hash-chained log; no record is "
        "changed or deleted.",
    },
    "audit_time": {KA: "დრო (UTC)", EN: "Time (UTC)"},
    "audit_event": {KA: "მოვლენა", EN: "Event"},
    "audit_outcome": {KA: "შედეგი", EN: "Outcome"},
    "vehicle": {KA: "ავტომობილი", EN: "Vehicle"},
    "collateral_case": {KA: "გირაოს ნიმუში", EN: "Collateral case"},
    "requested_amount": {KA: "მოთხოვნილი", EN: "Requested"},
    "binding_limit": {KA: "შემზღუდველი ლიმიტი: {limit}", EN: "Binding limit: {limit}"},
    "income_recommendation": {KA: "შემოსავლის შეფასება", EN: "Income assessment"},
    "pti": {
        KA: "PTI მოთხოვნილ თანხაზე / ლიმიტი",
        EN: "PTI at the requested amount / limit",
    },
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
