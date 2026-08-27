# Healthcare Claims, Provider & Enrollment Analytics

An end-to-end Data Analyst portfolio project that generates fictional healthcare operations data, applies audit-ready controls, loads a SQLite dimensional model, and produces claims, provider, enrollment, contract, reconciliation, and data-quality reporting.

> **All data is synthetic and created solely for portfolio demonstration. No PHI or confidential employer data is used.** This is an independent project. It is not a Norton Healthcare project, does not use Norton Healthcare data or branding, and does not represent a production deployment.

## Overview

The project demonstrates a repeatable analytical workflow rather than a collection of disconnected queries. A fixed-seed generator creates synthetic member, provider, contract, enrollment, and claim sources. Python validates business rules, quarantines unsafe records, proves source-to-target completeness, loads constrained facts and dimensions, calculates operational and financial KPIs, and publishes dashboard-ready files.

## Business Problem

Healthcare analytics teams need consistent answers to practical questions:

- Are claim, member, provider, enrollment, and contract references complete?
- Do paid amounts comply with allowed amounts?
- Was the member enrolled on the service date?
- Which providers, specialties, plans, and contracts drive cost and utilization?
- Do source counts and financial amounts reconcile to the analytical model?
- Can exceptions and management findings be reproduced for audit support?

This repository implements those controls using privacy-conscious synthetic data concepts. It does not claim HIPAA certification or operational use in a healthcare organization.

## Architecture

```text
Fixed-seed synthetic sources
 members │ providers │ contracts │ enrollment │ claims
                           │
                           ▼
          reference, domain, date, amount, eligibility checks
                           │
             ┌─────────────┴─────────────┐
             ▼                           ▼
 validated claim facts          quarantine + exception evidence
             └─────────────┬─────────────┘
                           ▼
              source-to-target reconciliation
                           ▼
                constrained SQLite model
                           ▼
 claims │ provider │ contract │ enrollment │ outlier analytics
                           ▼
      CSV dashboards │ JSON evidence │ Markdown business report
```

Repository layout:

```text
data/raw/          generated fictional CSV sources
data/processed/    generated SQLite analytical database
src/               generation, quality, ETL, analytics, reporting
sql/               schema and business-focused analytical queries
tests/             standard-library unit tests
outputs/           versioned dashboard and audit-support extracts
docs/              data dictionary and business-rule documentation
```

## Dataset

The deterministic run uses seed `20260827` and creates:

- 1,500 fictional members with fake `SYNM######` identifiers;
- 160 fictional provider organizations;
- 24 fictional contracts;
- 1,500 enrollment spans;
- 12,000 unique claims and 12,008 source claim rows.

Controlled test conditions include 8 duplicate claims, 12 invalid provider references, 15 services outside enrollment, 10 paid-over-allowed claims, 10 missing diagnosis categories, and 18 high-cost spikes. No source record represents a real person, provider, encounter, or payment.

## Data Model

SQLite uses `dim_member`, `dim_provider`, `dim_plan`, and `dim_contract`, plus `fact_enrollment` and `fact_claim`. `claim_quarantine`, `claim_quality_exception`, and `etl_control` preserve rejected records and control evidence. Primary keys, foreign keys, domain checks, financial constraints, and indexes enforce the analytical contract. Currency is stored as integer cents.

See [`sql/schema.sql`](sql/schema.sql) and the [data dictionary](docs/data_dictionary.md).

## ETL

```text
generate_synthetic_data
  → validate_reference_data / validate_claims
  → deterministic claim deduplication
  → typed transformation to integer cents
  → quarantine unsafe financial/reference records
  → reconcile source count and three amount measures
  → transactional SQLite load
  → calculate claims, provider, enrollment, contract, and outlier analytics
  → generate six reporting artifacts
```

Critical member, contract, plan, domain, parsing, or reconciliation failures raise `DataQualityError` and stop reporting. Expected portfolio anomalies remain traceable rather than disappearing silently.

## Healthcare Business Rules

Controls validate unique claim IDs, member and provider references, provider-contract and member-plan relationships, financial hierarchy, claim domains, enrollment eligibility, required analytical fields, enrollment dates, and high-cost thresholds. Invalid providers and paid-over-allowed claims are quarantined; eligibility and completeness issues are retained with review flags.

The complete rule catalog and severity decisions are documented in [`docs/business_rules.md`](docs/business_rules.md).

## Claims Analytics

The claims layer calculates monthly volume, billed/allowed/paid amounts, average claim value, denial/rejection rate, processing time, cost spikes, claim-type mix, paid-to-allowed rate, and month-over-month financial trends.

## Enrollment Analytics

Monthly reporting includes active members, new enrollments, terminations, utilizing members, claims per 1,000 members, and paid PMPM. Plan-level analysis compares membership, utilization, and paid value without many-to-many join inflation.

## Provider Analytics

Provider and specialty reporting measures claim volume, billed/allowed/paid amounts, denial rate, average paid cost, actual contract discount, variance to target, paid-cost rank, and z-score outlier status. Contract summaries support performance and ad hoc variance analysis.

## Data Quality

The reproducible run reports zero critical errors. The source population is reconciled as:

```text
12,000 unique source claims = 11,978 loaded claims + 22 quarantined claims
```

Billed, allowed, and paid amounts also reconcile exactly in integer cents. The JSON control file preserves generated counts, detected issues, duplicate IDs, quarantine IDs, and every reconciliation result.

## SQL Examples

The SQL solves actual analytical and control problems:

- [`claims_analysis.sql`](sql/claims_analysis.sql): CTE-based monthly trends, `LAG`, claim-type cost contribution, and high-cost `ROW_NUMBER` ranking;
- [`provider_analysis.sql`](sql/provider_analysis.sql): provider/contract joins, ranking, specialty benchmarks, `HAVING`, and variance to contract target;
- [`enrollment_analysis.sql`](sql/enrollment_analysis.sql): recursive monthly calendar, eligibility-aware active membership, paid PMPM, utilization, and plan summaries;
- [`reconciliation.sql`](sql/reconciliation.sql): persisted control evidence, enrollment-date exceptions, and loaded-plus-quarantine financial reconciliation;
- [`data_quality.sql`](sql/data_quality.sql): uniqueness, reference, financial, missing-field, and exception checks.

## Outputs

| File | Business use |
|---|---|
| `outputs/claims_kpis.csv` | Monthly Power BI/Tableau-ready financial and denial KPIs |
| `outputs/provider_summary.csv` | Provider, specialty, contract, variance, and outlier analysis |
| `outputs/enrollment_summary.csv` | Membership, utilization, and paid PMPM trend |
| `outputs/reconciliation_report.csv` | Count and financial source-to-target controls |
| `outputs/data_quality_report.json` | Machine-readable audit and validation evidence |
| `outputs/healthcare_business_report.md` | Calculated findings and recommendations |

## Testing

Eleven `unittest` tests cover duplicate handling, invalid member/provider relationships, paid-over-allowed logic, enrollment-date validation, integer-cent transformation, calculated KPIs, reconciliation success/failure, and report generation from calculated facts.

## How to Run

Requires Python 3.11 or later. No paid APIs, private keys, or third-party runtime packages are required.

```bash
git clone https://github.com/kotha-sricharan/healthcare-claims-provider-enrollment-analytics.git
cd healthcare-claims-provider-enrollment-analytics

python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt

python -m src.run_pipeline
python -m unittest discover -s tests -v
```

Or use:

```bash
make verify
```

## Business Findings

The deterministic demonstration run produces these calculated findings:

- 11,978 loaded claims covering all 1,500 synthetic members;
- $32.01M billed, $23.93M allowed, and $17.97M paid;
- 11.78% denial/rejection rate and $2,672.79 average billed claim value;
- October is the highest-paid and highest-utilization month;
- Orthopedics has the highest specialty paid amount at $2.56M;
- six provider cost outliers based on average-paid z-scores;
- 22 financially/reference-unsafe claims quarantined;
- all four source-to-target reconciliation controls pass exactly.

These findings describe generated test data only.

## Recommendations

1. Review denial and rejection edits by provider and claim type.
2. Validate provider identifiers against the master file before adjudication.
3. Block payment release when paid amount exceeds allowed amount.
4. Run eligibility checks before adjudication and retain override evidence.
5. Route high-cost claims and provider outliers to focused clinical and contract review.
6. Monitor utilization and paid PMPM monthly with plan and specialty drill-downs.

The generated Markdown report selects and quantifies recommendations from calculated results rather than a hard-coded narrative.

## Limitations

- All records, identifiers, costs, contracts, and findings are fictional.
- The project is not a clinical model, fraud model, actuarial forecast, or regulatory submission.
- Eligibility uses one enrollment span per member and exact dates; overlapping coverage and coordination of benefits are not modeled.
- Contract rules are illustrative and do not represent real payer/provider agreements.
- Amounts are synthetic USD and do not include real fee schedules, benefits, member cost share, reserves, or risk adjustment.
- SQLite and local files demonstrate analytical design; production access controls, orchestration, lineage, encryption, retention, and governed BI deployment are outside scope.
