PRAGMA foreign_keys = ON;

CREATE TABLE dim_plan (
    plan_id TEXT PRIMARY KEY,
    plan_type TEXT NOT NULL CHECK (plan_type IN ('HMO','PPO','EPO','HDHP')),
    metal_level TEXT NOT NULL CHECK (metal_level IN ('BRONZE','SILVER','GOLD'))
);

CREATE TABLE dim_contract (
    contract_id TEXT PRIMARY KEY,
    contract_name TEXT NOT NULL,
    contract_type TEXT NOT NULL CHECK (contract_type IN ('FFS','VALUE_BASED','SHARED_SAVINGS')),
    effective_start TEXT NOT NULL,
    effective_end TEXT NOT NULL,
    target_discount_rate REAL NOT NULL CHECK (target_discount_rate BETWEEN 0 AND 1),
    quality_target REAL NOT NULL CHECK (quality_target BETWEEN 0 AND 1),
    active_flag TEXT NOT NULL CHECK (active_flag IN ('Y','N'))
);

CREATE TABLE dim_member (
    member_id TEXT PRIMARY KEY,
    age_band TEXT NOT NULL,
    risk_segment TEXT NOT NULL CHECK (risk_segment IN ('LOW','MEDIUM','HIGH')),
    region TEXT NOT NULL,
    member_status TEXT NOT NULL CHECK (member_status IN ('ACTIVE','TERMINATED'))
);

CREATE TABLE dim_provider (
    provider_id TEXT PRIMARY KEY,
    provider_name TEXT NOT NULL,
    provider_specialty TEXT NOT NULL,
    region TEXT NOT NULL,
    contract_id TEXT NOT NULL REFERENCES dim_contract(contract_id),
    provider_status TEXT NOT NULL CHECK (provider_status IN ('ACTIVE','INACTIVE'))
);

CREATE TABLE fact_enrollment (
    enrollment_id TEXT PRIMARY KEY,
    member_id TEXT NOT NULL REFERENCES dim_member(member_id),
    plan_id TEXT NOT NULL REFERENCES dim_plan(plan_id),
    enrollment_start TEXT NOT NULL,
    enrollment_end TEXT NOT NULL,
    coverage_status TEXT NOT NULL CHECK (coverage_status IN ('ACTIVE','TERMINATED')),
    CHECK (enrollment_start <= enrollment_end)
);

CREATE TABLE fact_claim (
    claim_id TEXT PRIMARY KEY,
    member_id TEXT NOT NULL REFERENCES dim_member(member_id),
    provider_id TEXT NOT NULL REFERENCES dim_provider(provider_id),
    contract_id TEXT NOT NULL REFERENCES dim_contract(contract_id),
    plan_id TEXT NOT NULL REFERENCES dim_plan(plan_id),
    service_date TEXT NOT NULL,
    service_month TEXT NOT NULL,
    claim_type TEXT NOT NULL CHECK (claim_type IN ('PROFESSIONAL','OUTPATIENT','INPATIENT','PHARMACY')),
    claim_amount_cents INTEGER NOT NULL CHECK (claim_amount_cents >= 0),
    allowed_amount_cents INTEGER NOT NULL CHECK (allowed_amount_cents BETWEEN 0 AND claim_amount_cents),
    paid_amount_cents INTEGER NOT NULL CHECK (paid_amount_cents BETWEEN 0 AND allowed_amount_cents),
    claim_status TEXT NOT NULL CHECK (claim_status IN ('PAID','DENIED','REJECTED','PENDING')),
    diagnosis_category TEXT,
    source_system TEXT NOT NULL,
    processing_days INTEGER CHECK (processing_days IS NULL OR processing_days >= 0),
    quality_flag TEXT NOT NULL
);

CREATE TABLE claim_quarantine (
    claim_id TEXT PRIMARY KEY,
    member_id TEXT,
    source_provider_id TEXT,
    contract_id TEXT,
    service_date TEXT,
    claim_amount_cents INTEGER NOT NULL,
    allowed_amount_cents INTEGER NOT NULL,
    paid_amount_cents INTEGER NOT NULL,
    quarantine_reason TEXT NOT NULL
);

CREATE TABLE claim_quality_exception (
    exception_id TEXT PRIMARY KEY,
    claim_id TEXT NOT NULL,
    issue_type TEXT NOT NULL,
    severity TEXT NOT NULL CHECK (severity IN ('LOW','MEDIUM','HIGH')),
    action TEXT NOT NULL CHECK (action IN ('DEDUPLICATE','QUARANTINE','REVIEW'))
);

CREATE TABLE etl_control (
    control_name TEXT PRIMARY KEY,
    source_value INTEGER NOT NULL,
    target_value INTEGER NOT NULL,
    difference INTEGER NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('PASS','FAIL'))
);

CREATE INDEX idx_claim_service_month ON fact_claim(service_month);
CREATE INDEX idx_claim_provider_month ON fact_claim(provider_id, service_month);
CREATE INDEX idx_claim_member_date ON fact_claim(member_id, service_date);
CREATE INDEX idx_claim_contract ON fact_claim(contract_id);
CREATE INDEX idx_enrollment_member_dates ON fact_enrollment(member_id, enrollment_start, enrollment_end);
CREATE INDEX idx_quality_issue ON claim_quality_exception(issue_type, action);
