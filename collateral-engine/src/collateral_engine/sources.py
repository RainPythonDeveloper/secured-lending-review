"""Where every Georgian and NBG fact in the platform comes from, listed on the Overview page.

Each source says what it backs in the platform and how strong it is: an NBG act or law, an
official publication, a service the platform calls at run time, or a press report of an official
decision that still has to be checked against the act itself.
"""

from dataclasses import dataclass
from enum import StrEnum

from collateral_engine.i18n import Bilingual, Language

KA, EN = Language.GEORGIAN, Language.ENGLISH


class SourceKind(StrEnum):
    LEGAL_ACT = "legal_act"
    OFFICIAL = "official"
    LIVE_SERVICE = "live_service"
    PRESS_REPORT = "press_report"


class SourceGroup(StrEnum):
    REGULATION = "regulation"
    MARKET = "market"
    DATA = "data"


@dataclass(frozen=True)
class Source:
    group: SourceGroup
    kind: SourceKind
    publisher: str
    title: str
    date: str
    url: str | None
    used_for: Bilingual
    caveat: Bilingual | None = None


SOURCES: tuple[Source, ...] = (
    Source(
        SourceGroup.REGULATION,
        SourceKind.LEGAL_ACT,
        "National Bank of Georgia",
        "Order No. 84/04, Real Estate Valuation Instruction for Commercial Banks "
        "(კომერციული ბანკებისათვის უძრავი ქონების შეფასების ინსტრუქცია)",
        "14 May 2018",
        "https://matsne.gov.ge/ka/document/view/4190992",
        {
            KA: "მინიმუმ 3 ანალოგი; თითო კორექტირება ±15%, ჯამური ±25% (დასაბუთებით ±35%), "
            "მუხ. 4(5); შემფასებლის ანგარიშის შემოწმება.",
            EN: "At least 3 comparables; each adjustment within ±15%, gross within ±25% (±35% "
            "with a justification), Art. 4(5); the check of a valuer's report.",
        },
        {
            KA: "გამოყენებულია 2018 წლის ტექსტი; შემდგომი ცვლილებები მუხლობრივად არ შემოწმებულა.",
            EN: "Read in its 2018 text; later amendments not checked article by article.",
        },
    ),
    Source(
        SourceGroup.REGULATION,
        SourceKind.LEGAL_ACT,
        "National Bank of Georgia",
        "Order No. 44/04, Regulation on Lending to Natural Persons "
        "(ფიზიკური პირის დაკრედიტების შესახებ დებულება)",
        "13 March 2020",
        "https://matsne.gov.ge/ka/document/view/4822603",
        {
            KA: "PTI და LTV ლიმიტები; სხვა ვალდებულებების გადასახადი PTI-ში ითვლება.",
            EN: "PTI and LTV limits; payments on existing obligations count towards PTI.",
        },
    ),
    Source(
        SourceGroup.REGULATION,
        SourceKind.OFFICIAL,
        "National Bank of Georgia",
        "PTI and LTV Requirements",
        "current page",
        "https://nbg.gov.ge/en/page/pti-and-ltv-requirements",
        {
            KA: "PTI: შემოსავალი 1 500 ლარამდე — 25% (ლარი) / 20% (ვალუტა), ზემოთ — 50% / 30%; "
            "LTV: 90% ლარი / 70% ვალუტა.",
            EN: "PTI: income below 1,500 GEL 25% (GEL) / 20% (foreign currency), above it "
            "50% / 30%; LTV: 90% GEL / 70% foreign currency.",
        },
    ),
    Source(
        SourceGroup.REGULATION,
        SourceKind.OFFICIAL,
        "National Bank of Georgia",
        "Financial Stability Committee's Decision",
        "26 February 2025",
        "https://nbg.gov.ge/en/media/news/financial-stability-committee-s-decis-14",
        {
            KA: "LTV დროებით 90%-მდე ლარის სესხებზე; 80% უცხოეთიდან შემოსავლის მქონე "
            "მსესხებლების ვალუტის იპოთეკაზე.",
            EN: "LTV raised temporarily to 90% for GEL loans and to 80% for foreign-currency "
            "mortgages of borrowers with income from abroad.",
        },
        {
            KA: "ძალაში შესვლის თარიღად აღებულია გამოქვეყნების თარიღი.",
            EN: "The publication date is taken as the effective date.",
        },
    ),
    Source(
        SourceGroup.REGULATION,
        SourceKind.OFFICIAL,
        "National Bank of Georgia",
        "The National Bank of Georgia has approved the regulation on responsible lending to "
        "natural persons",
        "n.d.",
        "https://nbg.gov.ge/en/media/news/the-national-bank-of-georgia-has-approved-the-"
        "regulation-on-responsible-lending-to-natural",
        {
            KA: "საბაზისო LTV შემსუბუქებამდე: 85% ლარი / 70% ვალუტა.",
            EN: "The LTV before the easing: 85% GEL / 70% foreign currency.",
        },
    ),
    Source(
        SourceGroup.REGULATION,
        SourceKind.LEGAL_ACT,
        "National Bank of Georgia",
        "Order No. 104/04 on the electronic application of preventive measures by an "
        "accountable person (remote identification)",
        "29 April 2025",
        "https://nbg.gov.ge/fm/ინდივიდუალურ_სამართლებრივი_აქტები/ნორმატიული_აქტები/"
        "ფულის_გათეთრება/2025/104-04.pdf",
        {
            KA: "დისტანციური იდენტიფიკაცია: მინიმუმ 3 შემთხვევითი დავალება, მაქსიმუმ 3 მცდელობა "
            "24 საათში.",
            EN: "Remote identification: at least 3 randomly chosen tasks, at most 3 attempts in "
            "24 hours.",
        },
    ),
    Source(
        SourceGroup.REGULATION,
        SourceKind.LEGAL_ACT,
        "National Bank of Georgia",
        "Decree No. 151/04, Regulation on Data-driven Statistical, AI and Machine Learning "
        "Model Risk Management",
        "17 August 2020",
        "https://nbg.gov.ge/fm/ზედამხედველობა/ფინტექ_დეპარტამენტი/მოდელ_რისკი/mrm-151-04eng.pdf",
        {
            KA: "მოდელის რისკის კონტროლის საფუძველი: ახსნადობა, ოფიცრის გადაწყვეტილებების "
            "ანალიზი, მოდელების ვერსიები და აუდიტი.",
            EN: "The basis of the model risk controls: explainability, analysis of officer "
            "overrides, model versions and audit.",
        },
    ),
    Source(
        SourceGroup.REGULATION,
        SourceKind.LEGAL_ACT,
        "Parliament of Georgia",
        "Law of Georgia on Personal Data Protection",
        "2023, in force 1 March 2024",
        "https://matsne.gov.ge/en/document/view/5827307",
        {
            KA: "ბიომეტრია განსაკუთრებული კატეგორიაა: სახის შაბლონი არ იქმნება, კადრები არ "
            "ინახება, არასრულწლოვნებს არ ვიღებთ; გადაწყვეტილებას ადამიანი იღებს.",
            EN: "Biometric data is a special category: no face template, frames not stored, "
            "no minors filmed; a person makes the decision.",
        },
    ),
    Source(
        SourceGroup.REGULATION,
        SourceKind.OFFICIAL,
        "National Bank of Georgia",
        "Open Banking",
        "current page",
        "https://nbg.gov.ge/en/page/open-banking",
        {
            KA: "Open Banking-ის ჩარჩო (Berlin Group): კლიენტის თანხმობით ანგარიშების მონაცემები.",
            EN: "The Open Banking framework (Berlin Group): account data with the customer's "
            "consent.",
        },
    ),
    Source(
        SourceGroup.REGULATION,
        SourceKind.OFFICIAL,
        "National Bank of Georgia",
        "Credit Bureau Supervision",
        "current page",
        "https://nbg.gov.ge/en/page/credit-bureau-supervision",
        {
            KA: "საკრედიტო ისტორიის ეტაპი Creditinfo Georgia-ს სინთეტიკური შემცვლელია.",
            EN: "The credit history stage is a synthetic stand-in for Creditinfo Georgia.",
        },
    ),
    Source(
        SourceGroup.REGULATION,
        SourceKind.PRESS_REPORT,
        "Georgia Today",
        "Georgia to tighten lending rules from February 2027",
        "30 September 2026",
        "https://georgiatoday.ge/georgia-to-tighten-lending-rules-from-february-2027/",
        {
            KA: "25%-იანი PTI-ის ზღვარი: 2 000 ლარი 2027-02-01-დან, 2 500 ლარი 2027-09-01-დან.",
            EN: "The 25% PTI threshold: 2,000 GEL from 1 Feb 2027, 2,500 GEL from 1 Sep 2027.",
        },
    ),
    Source(
        SourceGroup.REGULATION,
        SourceKind.PRESS_REPORT,
        "Georgia Today",
        "NBG raises foreign currency loan threshold to 1 million GEL",
        "2026",
        "https://georgiatoday.ge/nbg-raises-foreign-currency-loan-threshold-to-1-million-gel/",
        {
            KA: "1 000 000 ლარამდე სესხი მხოლოდ ლარში, 2026-07-01-დან.",
            EN: "Loans below 1,000,000 GEL only in GEL, from 1 Jul 2026.",
        },
    ),
    Source(
        SourceGroup.REGULATION,
        SourceKind.PRESS_REPORT,
        "1TV (Georgian Public Broadcaster)",
        "Georgia increases foreign currency loan limit to GEL 750,000 from August 1",
        "2025",
        "https://1tv.ge/lang/en/news/georgia-increases-foreign-currency-loan-limit-to-gel-"
        "750000-from-august-1/",
        {
            KA: "750 000 ლარამდე სესხი მხოლოდ ლარში, 2025-08-01-დან.",
            EN: "Loans below 750,000 GEL only in GEL, from 1 Aug 2025.",
        },
        {
            KA: "ერთი სხვა ანგარიში სექტემბრის თარიღს ასახელებს.",
            EN: "Another report gives a September date.",
        },
    ),
    Source(
        SourceGroup.REGULATION,
        SourceKind.PRESS_REPORT,
        "Georgia Today",
        "National Bank of Georgia Extends Maximum Maturity of Unsecured Consumer Loans to 4 Years",
        "18 October 2023",
        "https://georgiatoday.ge/national-bank-of-georgia-extends-maximum-maturity-of-"
        "unsecured-consumer-loans-to-4-years/",
        {
            KA: "უზრუნველყოფის გარეშე სამომხმარებლო სესხის მაქსიმალური ვადა 4 წელი.",
            EN: "The longest term of an unsecured consumer loan: 4 years.",
        },
        {
            KA: "ავტოსესხზე ამ ლიმიტის გავრცელება ჩვენი დაშვებაა.",
            EN: "Applying it to car loans is our assumption.",
        },
    ),
    Source(
        SourceGroup.REGULATION,
        SourceKind.PRESS_REPORT,
        "Civil.ge",
        "Georgia's Central Bank Eases Loan Rules for Natural Persons",
        "2020",
        "https://oldwp.civil.ge/archives/342730",
        {
            KA: "ლარის იპოთეკის მაქსიმალური ვადა 20 წელი.",
            EN: "The longest term of a GEL mortgage: 20 years.",
        },
    ),
    Source(
        SourceGroup.REGULATION,
        SourceKind.PRESS_REPORT,
        "GBC (Georgian Business Channel)",
        "Mortgages in USD have also become more expensive",
        "2022",
        "https://gbc.ge/en/news/finanse/mortgages-in-usd-have-also-become-more-expensive",
        {
            KA: "ვალუტის იპოთეკის მაქსიმალური ვადა 10 წელი.",
            EN: "The longest term of a foreign-currency mortgage: 10 years.",
        },
    ),
    Source(
        SourceGroup.MARKET,
        SourceKind.OFFICIAL,
        "Geostat (National Statistics Office of Georgia)",
        "Residential Property Price Index, II quarter of 2026",
        "23 July 2026",
        "https://geostat.ge/media/81560/Residential-Property-Price-Index---II-quarter-of-2026.pdf",
        {
            KA: "კერძო სახლები +5,5% წელიწადში; შავი, თეთრი და მწვანე კარკასი; შეთავაზების ფასები "
            "myhome.ge-დან და ss.ge-დან.",
            EN: "Private houses +5.5% a year; the black, white and green frame classes; offer "
            "prices from myhome.ge and ss.ge.",
        },
    ),
    Source(
        SourceGroup.MARKET,
        SourceKind.PRESS_REPORT,
        "CBW, citing Geostat",
        "Tbilisi Property Prices Rise 11.5% Year-on-Year in Q1, Led by Mtatsminda and Vake "
        "Districts",
        "2026",
        "https://cbw.ge/real-estate/tbilisi-property-prices-rise-115-year-on-year-in-q1-led-by-"
        "mtatsminda-and-vake-districts",
        {
            KA: "ახალი ბინების 1 მ²-ის ფასი თბილისის 10 რაიონში, I კვ. 2026 — სინთეტიკური ბაზრის "
            "საყრდენი.",
            EN: "Price per m² of new flats in the ten Tbilisi districts, Q1 2026: the anchors "
            "of the synthetic market.",
        },
    ),
    Source(
        SourceGroup.MARKET,
        SourceKind.PRESS_REPORT,
        "1TV, citing Geostat",
        "Geostat: Residential real estate prices rise in Tbilisi in Q1 2026",
        "2026",
        "https://1tv.ge/lang/en/news/geostat-residential-real-estate-prices-rise-in-tbilisi-in-"
        "q1-2026/",
        {
            KA: "ახალი კერძო სახლების 1 მ²-ის ფასი რაიონების მიხედვით, I კვ. 2026.",
            EN: "Price per m² of new private houses by district, Q1 2026.",
        },
    ),
    Source(
        SourceGroup.MARKET,
        SourceKind.OFFICIAL,
        "International Monetary Fund (J. Mehrhoff)",
        "Georgia: Technical Assistance Report, Data for Decisions (D4D), Residential Property "
        "Price Index",
        "April 2025",
        "https://www.imf.org/-/media/files/publications/tar/2025/english/"
        "tarea2025049-print-pdf.pdf",
        {
            KA: "სახლის 1 მ²-ის ფასი სახლის ფართზეა; ნაკვეთი ცალკე მახასიათებელია.",
            EN: "A house's price per m² is per m² of the house; the plot is a separate "
            "characteristic.",
        },
    ),
    Source(
        SourceGroup.MARKET,
        SourceKind.OFFICIAL,
        "National Agency of Public Registry (NAPR)",
        "Public Registry",
        "current site",
        "https://napr.gov.ge/en",
        {
            KA: "საკადასტრო კოდი; რეესტრი ფასების ღია მონაცემებს არ აქვეყნებს.",
            EN: "The cadastral code; the registry publishes no open transaction prices.",
        },
        {
            KA: "კოდის ფორმატი რეესტრის ამონაწერებიდანაა აღებული; წესი არ შემოწმებულა.",
            EN: "The code format is inferred from registry extracts; the rule is not verified.",
        },
    ),
    Source(
        SourceGroup.DATA,
        SourceKind.LIVE_SERVICE,
        "National Bank of Georgia",
        "Official exchange rates API",
        "called at run time",
        "https://nbg.gov.ge/gw/api/ct/monetarypolicy/currencies/en/json/",
        {
            KA: "ლარის კურსი სებ-ის ოფიციალური კურსით; ყოველი პასუხის თარიღი მოწმდება.",
            EN: "GEL amounts at the official NBG rate; the date of every answer is checked.",
        },
    ),
    Source(
        SourceGroup.DATA,
        SourceKind.LIVE_SERVICE,
        "TBC Bank (hackathon sandbox)",
        "Mock Open Banking API, OpenAPI specification",
        "called at run time",
        "https://tbc-bank-mock-open-banking-api.vercel.app/openapi.json",
        {
            KA: "თანხმობა, ანგარიშები, ნაშთები და ტრანზაქციები Open Banking შლუზის გავლით.",
            EN: "Consent, accounts, balances and transactions through the Open Banking gateway.",
        },
    ),
    Source(
        SourceGroup.DATA,
        SourceKind.OFFICIAL,
        "NBG AI & Open Banking Hackathon organisers",
        "Synthetic dataset: 100 customers, six months of transactions",
        "October 2026",
        None,
        {
            KA: "არსებული კლიენტები და მათი ამონაწერები (data/open-banking-synthetic-100-"
            "customers.xlsx).",
            EN: "The existing customers and their statements "
            "(data/open-banking-synthetic-100-customers.xlsx).",
        },
    ),
    Source(
        SourceGroup.DATA,
        SourceKind.OFFICIAL,
        "OpenStreetMap contributors (ODbL 1.0)",
        "Tbilisi metro stations",
        "22 October 2026",
        "https://www.openstreetmap.org/copyright",
        {
            KA: "მანძილი უახლოეს მეტრომდე (23 სადგური).",
            EN: "Distance to the nearest of 23 metro stations.",
        },
    ),
)

GROUP_NAMES: dict[SourceGroup, Bilingual] = {
    SourceGroup.REGULATION: {KA: "სებ-ის რეგულაცია და კანონები", EN: "NBG regulation and law"},
    SourceGroup.MARKET: {KA: "ბაზარი და სტატისტიკა", EN: "Market and statistics"},
    SourceGroup.DATA: {KA: "მონაცემები და სერვისები", EN: "Data and services"},
}

SOURCE_KIND_NAMES: dict[SourceKind, Bilingual] = {
    SourceKind.LEGAL_ACT: {KA: "სამართლებრივი აქტი", EN: "Legal act"},
    SourceKind.OFFICIAL: {KA: "ოფიციალური წყარო", EN: "Official source"},
    SourceKind.LIVE_SERVICE: {KA: "ცოცხალი სერვისი", EN: "Live service"},
    SourceKind.PRESS_REPORT: {KA: "პრესა · გადასამოწმებელი", EN: "Press report · to verify"},
}
