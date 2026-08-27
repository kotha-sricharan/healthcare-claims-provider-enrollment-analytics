-- Fact-table uniqueness and reference-integrity checks should return no rows.
SELECT claim_id, COUNT(*) AS row_count
FROM fact_claim
GROUP BY claim_id
HAVING COUNT(*) > 1;

SELECT f.claim_id
FROM fact_claim f
LEFT JOIN dim_member m ON m.member_id = f.member_id
LEFT JOIN dim_provider p ON p.provider_id = f.provider_id
LEFT JOIN dim_contract c ON c.contract_id = f.contract_id
WHERE m.member_id IS NULL OR p.provider_id IS NULL OR c.contract_id IS NULL;

-- Financial rule enforcement should return no loaded claims.
SELECT claim_id, allowed_amount_cents, paid_amount_cents
FROM fact_claim
WHERE paid_amount_cents > allowed_amount_cents
   OR allowed_amount_cents > claim_amount_cents
   OR claim_amount_cents < 0;

-- Controlled source issues retained for audit and remediation reporting.
SELECT issue_type, action, severity, COUNT(*) AS issue_count
FROM claim_quality_exception
GROUP BY issue_type, action, severity
ORDER BY issue_count DESC, issue_type;

-- Missing analytical attributes by month support data-steward follow-up.
SELECT service_month, COUNT(*) AS missing_diagnosis_claims
FROM fact_claim
WHERE diagnosis_category IS NULL
GROUP BY service_month
HAVING COUNT(*) > 0
ORDER BY service_month;
