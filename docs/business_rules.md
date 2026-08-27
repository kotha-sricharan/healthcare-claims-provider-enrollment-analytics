# Healthcare Analytics Business Rules

These rules govern fictional portfolio data only. They illustrate control design and do not replace payer policy, clinical review, legal advice, or jurisdiction-specific requirements.

## Control severity and pipeline behavior

| Classification | Pipeline behavior | Examples |
|---|---|---|
| Critical integrity failure | Stop the pipeline before loading or reporting | Unknown member, invalid status/domain, malformed amount/date, broken contract or plan relationship, failed source-to-target reconciliation |
| Quarantinable financial exception | Preserve in `claim_quarantine`, exclude from KPI facts, and reconcile separately | Invalid provider identifier, paid amount greater than allowed amount |
| Review exception | Load with a quality flag and retain an audit exception | Service outside enrollment, missing diagnosis category, unusual cost spike |
| Duplicate source row | Retain the first deterministic occurrence and record the duplicate ID | Repeated `claim_id` |

## Claim controls

1. **Unique claim identifier:** Each analytical claim must have one `claim_id`. Repeated IDs are removed using a stable first-row rule and recorded as `DUPLICATE_CLAIM`.
2. **Member reference:** `member_id` must exist in the member dimension and have one source enrollment span. An unknown member is critical because eligibility and utilization attribution cannot be established.
3. **Provider reference:** `provider_id` must exist in the provider dimension. Unknown providers are quarantined so provider and contract KPIs cannot be misstated.
4. **Contract consistency:** Claim `contract_id` must exist and must equal the provider's assigned contract. A mismatch is critical.
5. **Plan consistency:** Claim `plan_id` must equal the member's enrollment plan. A mismatch is critical.
6. **Financial hierarchy:** Billed, allowed, and paid values must be numeric and nonnegative. Allowed cannot exceed billed. Paid cannot exceed allowed; those records are quarantined.
7. **Claim domains:** Claim status must be `PAID`, `DENIED`, `REJECTED`, or `PENDING`. Claim type must be `PROFESSIONAL`, `OUTPATIENT`, `INPATIENT`, or `PHARMACY`.
8. **Enrollment eligibility:** Service date should fall between enrollment start and end, inclusive. Out-of-coverage claims are retained as review exceptions to support eligibility analysis.
9. **Required analytical fields:** Missing diagnosis category is recorded for data-steward follow-up. Structural identifiers, dates, domains, and financial values cannot be missing.
10. **High-cost review:** A billed amount above $50,000 is flagged as a cost spike. This is an analytical review threshold, not an accusation of error or fraud.

## Reference-data controls

- Member, provider, contract, enrollment, and plan keys must be unique.
- Every provider must reference a valid contract.
- Every enrollment must reference a valid member and plan.
- Enrollment start must be on or before enrollment end.
- The synthetic source permits one enrollment span per member; multiple rows are critical because overlap resolution is outside this demonstration.

## Reconciliation controls

The ETL proves all of the following before publishing reports:

- unique source claims = loaded claims + quarantined claims;
- source billed cents = loaded billed cents + quarantined billed cents;
- source allowed cents = loaded allowed cents + quarantined allowed cents;
- source paid cents = loaded paid cents + quarantined paid cents.

All monetary comparisons use integer cents. Any nonzero difference raises `DataQualityError` and stops reporting.

## KPI definitions

- **Denial/rejection rate:** denied or rejected loaded claims divided by all loaded claims.
- **Actual discount rate:** 1 − total allowed / total billed.
- **Discount variance points:** actual discount rate minus contract target discount rate.
- **Claims per 1,000 members:** monthly loaded claim volume divided by active enrollment, multiplied by 1,000.
- **Paid PMPM:** monthly paid amount divided by active enrollment.
- **Provider cost outlier:** absolute z-score of average paid amount per claim at least 2.5.
