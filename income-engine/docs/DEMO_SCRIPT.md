# Demo video script (3:00) and pitch outline

Record the Streamlit app with OBS at 1920×1080, uncut, with voice-over. Keep the synthetic-data banner visible.

| Time | Screen | Voice-over |
|---|---|---|
| 0:00–0:20 | Sidebar → "Giorgi — Kakheti vineyard owner" | "This is Nino, a loan officer in Telavi. Giorgi grows grapes in Kakheti, has no credit history and asks for 8,000 lari. All data here is synthetic." |
| 0:20–0:50 | Top cards + income chart | "He declared 1,099 lari a month. From 18 months of consented transactions the engine estimates about 1,320, in a band of 1,085 to 1,350. Most of it arrives in August to October. Own transfers, gifts and circular money are removed." |
| 0:50–1:50 | NBG checks → reasons → path to yes → seasonal chart | "At 8,000 over 12 months his payments would take 64% of his income; NBG's limit for him is 25%. The engine offers 3,100, the largest compliant amount, and default risk drops from 41% to 6%. Here's why, in Georgian and English. Path to yes: over 48 months he qualifies for the full 8,000. And a harvest-shaped schedule cuts default risk for borrowers like him by about a fifth." |
| 1:50–2:30 | Officer decision → override without reason (error) → record → audit hash; then sidebar "Levan" → circular-transfer warning | "Nino decides, not the model. Disagreeing requires a reason, and every decision goes into a tamper-evident log. Second case: Levan declared 4,200 lari, but 43% of his client inflows are sent straight back. The engine estimates about 2,900 and sends him to review." |
| 2:30–3:00 | Portfolio results tab, then Supervisor tab | "On 3,671 out-of-time applications: 84% approved instead of 55%, at a lower bad rate, 1,155 thin-file borrowers included, income error cut from 13% to 5%. And for NBG: the impact of the 2027 PTI thresholds, computed by the same rules engine." |

## 10-slide deck (4-minute pitch)

1. **Hook.** "Giorgi earns about 1,300 lari a month. On paper he earns 1,099 and has no credit history. Today he's rejected or over-lent."
2. **Problem.** NBG's four pain points: bureau-only scoring, thin files excluded, misstated income, manual processes.
3. **Users & workflow.** Loan officer at a bank/MFI; risk manager; NBG supervisor. Before/after.
4. **Architecture.** Diagram from README. Track: AI in Finance, problem space 01.
5. **Data.** Synthetic, calibrated to Georgian patterns, hidden ground truth, out-of-time test, data card.
6. **What's new.** Income band, Georgian text, circular-transfer detection, max compliant loan, harvest-shaped schedule.
7. **Results.** Chart `reports/figures/approval_vs_bad_rate.png` + the results table from README.
8. **Guardrails.** Champion–challenger (scorecard won), sign checks, NBG rules engine, fairness, audit, stress test.
9. **Limitations.** Synthetic data, verified income labels, reject inference, PTI on seasonal schedules.
10. **Next step.** 3-month AI-sandbox pilot with one MFI on anonymised historical data.
