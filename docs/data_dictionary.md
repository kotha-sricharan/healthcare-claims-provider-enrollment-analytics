# Data Dictionary

All identifiers and records are generated and fictional. The project contains no patient names, addresses, Social Security numbers, medical record numbers, or other real-person identifiers.

## Raw synthetic sources

### `members.csv`

| Column | Type | Description |
|---|---|---|
| `member_id` | text | Fake key formatted `SYNM######` |
| `age_band` | text | Broad synthetic age category, not a date of birth |
| `risk_segment` | text | Illustrative LOW/MEDIUM/HIGH grouping |
| `region` | text | Fictional operating region |
| `member_status` | text | ACTIVE or TERMINATED based on enrollment end |

### `providers.csv`

| Column | Type | Description |
|---|---|---|
| `provider_id` | text | Fake key formatted `PRV####` |
| `provider_name` | text | Clearly labeled synthetic organization name |
| `provider_specialty` | text | Analytical specialty category |
| `region` | text | Fictional operating region |
| `contract_id` | text | Assigned synthetic contract |
| `provider_status` | text | ACTIVE or INACTIVE |

### `claims.csv`

| Column | Type | Description |
|---|---|---|
| `claim_id` | text | Fake key formatted `CLM#######` |
| `member_id` | text | Synthetic member reference |
| `provider_id` | text | Synthetic provider reference or controlled invalid value |
| `contract_id` | text | Synthetic provider contract reference |
| `plan_id` | text | Synthetic enrollment plan |
| `service_date` | ISO date | Fictional 2025 service date |
| `claim_type` | text | PROFESSIONAL, OUTPATIENT, INPATIENT, or PHARMACY |
| `claim_amount` | decimal | Billed amount in synthetic USD |
| `allowed_amount` | decimal | Contractually allowed synthetic amount |
| `paid_amount` | decimal | Synthetic adjudicated payment |
| `claim_status` | text | PAID, DENIED, REJECTED, or PENDING |
| `diagnosis_category` | text | Broad fictional analytical grouping; no clinical narrative |
| `source_system` | text | Synthetic source label |
| `processing_days` | integer | Days to synthetic disposition; blank for pending claims |

### `enrollment.csv`

| Column | Type | Description |
|---|---|---|
| `enrollment_id` | text | Fake enrollment key |
| `member_id` | text | Synthetic member reference |
| `plan_id` | text | Plan key |
| `plan_type` | text | HMO, PPO, EPO, or HDHP |
| `enrollment_start` | ISO date | Coverage start |
| `enrollment_end` | ISO date | Coverage end |
| `coverage_status` | text | ACTIVE or TERMINATED |

### `contracts.csv`

| Column | Type | Description |
|---|---|---|
| `contract_id` | text | Fake contract key |
| `contract_name` | text | Synthetic contract description |
| `contract_type` | text | FFS, VALUE_BASED, or SHARED_SAVINGS |
| `effective_start`, `effective_end` | ISO date | Synthetic effective period |
| `target_discount_rate` | decimal | Illustrative negotiated discount target |
| `quality_target` | decimal | Illustrative performance target |
| `active_flag` | text | Y or N |

## SQLite analytical model

| Table | Grain and purpose |
|---|---|
| `dim_member` | One row per fictional member |
| `dim_provider` | One row per fictional provider organization |
| `dim_plan` | One row per plan type |
| `dim_contract` | One row per synthetic contract |
| `fact_enrollment` | One enrollment span per fictional member |
| `fact_claim` | One validated, deduplicated, nonquarantined claim |
| `claim_quarantine` | One financially unsafe source claim retained for reconciliation |
| `claim_quality_exception` | One row per detected issue and claim |
| `etl_control` | One row per source-to-target control result |

Financial values in SQLite use integer cents to prevent floating-point reconciliation errors.

## Reporting outputs

| File | Grain |
|---|---|
| `claims_kpis.csv` | One row per service month |
| `provider_summary.csv` | One row per provider |
| `enrollment_summary.csv` | One row per month |
| `reconciliation_report.csv` | One row per count/amount control |
| `data_quality_report.json` | One machine-readable pipeline evidence package |
| `healthcare_business_report.md` | One calculated management summary |
