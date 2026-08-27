# Healthcare Claims, Provider & Enrollment Analytics Report

Reporting period: **2025-01 through 2025-12**
Data classification: **Synthetic portfolio data only — no PHI**

## Executive Summary

The governed pipeline loaded **11,978 analytically valid claims** covering **1,500 synthetic members**. The claims represent **$32,014,693.96 billed**, **$23,926,856.67 allowed**, and **$17,970,355.44 paid**. Source-to-target reconciliation status is **PASS**.

## Overall Claim Trends

- Denial/rejection rate: **11.78%** (1,411 claims).
- Average billed claim value: **$2,672.79**.
- Average processing time: **10.58 days**.
- Highest paid month: **2025-10** at **$2,127,419.71**.
- Controlled high-cost claims above the rule threshold: **18**.

## Provider & Contract Observations

**Synthetic Provider Organization 117** has the highest total paid amount at **$289,791.09** across **92 claims**. **Orthopedics** is the highest-paid specialty at **$2,556,704.47**. Provider cost z-scores flag **6** organizations for analytical review. The largest absolute contract discount variance belongs to **PRV0037** at **3.47 percentage points** versus target.

## Enrollment & Utilization Observations

Peak active enrollment is **1,322 members** in **2025-09**. Peak utilization occurs in **2025-10** at **1033.62 claims per 1,000 active members**, with paid PMPM of **$1,663.35**.

## Data Quality Findings

The source contains **12,008 rows** and **12,000 unique claim IDs**. The pipeline removed **8 duplicate IDs**, loaded **11,978 claims**, and quarantined **22 claims**. Critical validation errors: **0**.

| Controlled issue | Count |
|---|---:|
| Cost Spike | 18 |
| Duplicate Claim | 8 |
| Invalid Provider | 12 |
| Missing Required Field | 10 |
| Outside Enrollment | 15 |
| Paid Exceeds Allowed | 10 |

## Financial Reconciliation Findings

All **4** source-to-target count and amount controls passed. Unique source claims equal loaded plus quarantined claims, and billed, allowed, and paid amounts are conserved exactly in integer cents.

## Recommendations

1. Review denial and rejection edits by provider and claim type; the current rate is 11.78%.
2. Add provider-master validation at intake for the 12 claims currently quarantined for invalid provider identifiers.
3. Prevent payment release when paid exceeds allowed; 10 controlled exceptions were quarantined.
4. Run real-time eligibility checks before adjudication for the 15 claims outside enrollment dates.
5. Route the 18 high-cost claims to clinical and contract review, prioritizing statistically unusual providers.
6. Investigate utilization drivers in 2025-10, the peak month at 1033.62 claims per 1,000 members.

## Methodology

The workflow creates fictional members, providers, contracts, enrollment spans, and claims with a fixed seed. It validates identifiers, domains, amounts, eligibility, dates, and contract relationships; removes duplicate rows; quarantines financially unsafe records; loads a constrained SQLite dimensional model; reconciles counts and amounts; calculates monthly, provider, specialty, contract, enrollment, and outlier measures; and publishes flat audit-ready extracts.

All findings describe generated demonstration records. They do not represent real patients, members, providers, or healthcare operations.
