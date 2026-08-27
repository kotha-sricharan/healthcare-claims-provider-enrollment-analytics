-- Provider performance with contract targets and paid-cost ranking.
WITH provider_metrics AS (
    SELECT p.provider_id, p.provider_name, p.provider_specialty,
           c.contract_id, c.contract_type, c.target_discount_rate,
           COUNT(f.claim_id) AS claim_volume,
           SUM(f.claim_amount_cents) AS billed_cents,
           SUM(f.allowed_amount_cents) AS allowed_cents,
           SUM(f.paid_amount_cents) AS paid_cents,
           SUM(CASE WHEN f.claim_status IN ('DENIED','REJECTED') THEN 1 ELSE 0 END) AS denied_rejected
    FROM dim_provider p
    JOIN dim_contract c ON c.contract_id = p.contract_id
    LEFT JOIN fact_claim f ON f.provider_id = p.provider_id
    GROUP BY p.provider_id, p.provider_name, p.provider_specialty,
             c.contract_id, c.contract_type, c.target_discount_rate
)
SELECT *,
       ROUND(100.0 * denied_rejected / NULLIF(claim_volume,0), 2) AS denial_rejection_rate,
       ROUND(100.0 * (1.0 - allowed_cents * 1.0 / NULLIF(billed_cents,0)), 2) AS actual_discount_rate,
       ROUND(100.0 * ((1.0 - allowed_cents * 1.0 / NULLIF(billed_cents,0)) - target_discount_rate), 2) AS variance_to_target_points,
       RANK() OVER (ORDER BY paid_cents DESC) AS paid_cost_rank
FROM provider_metrics
ORDER BY paid_cost_rank;

-- Specialty cost and denial rates relative to the overall network.
WITH specialty AS (
    SELECT p.provider_specialty,
           COUNT(*) AS claim_volume,
           AVG(f.paid_amount_cents) AS average_paid_cents,
           100.0 * SUM(CASE WHEN f.claim_status IN ('DENIED','REJECTED') THEN 1 ELSE 0 END) / COUNT(*) AS denial_rate
    FROM fact_claim f
    JOIN dim_provider p ON p.provider_id = f.provider_id
    GROUP BY p.provider_specialty
)
SELECT provider_specialty, claim_volume,
       ROUND(average_paid_cents / 100.0, 2) AS average_paid_claim,
       ROUND(denial_rate, 2) AS denial_rate,
       ROUND(average_paid_cents / 100.0 - AVG(average_paid_cents / 100.0) OVER (), 2) AS variance_from_specialty_average
FROM specialty
ORDER BY average_paid_cents DESC;

-- Contracts with material deviation from negotiated discount targets.
SELECT c.contract_id, c.contract_type, COUNT(f.claim_id) AS claim_volume,
       ROUND(SUM(f.paid_amount_cents) / 100.0, 2) AS paid_amount,
       ROUND(100.0 * (1.0 - SUM(f.allowed_amount_cents) * 1.0 / SUM(f.claim_amount_cents)), 2) AS actual_discount_rate,
       ROUND(100.0 * ((1.0 - SUM(f.allowed_amount_cents) * 1.0 / SUM(f.claim_amount_cents)) - c.target_discount_rate), 2) AS variance_to_target_points
FROM dim_contract c
JOIN fact_claim f ON f.contract_id = c.contract_id
GROUP BY c.contract_id, c.contract_type, c.target_discount_rate
HAVING ABS((1.0 - SUM(f.allowed_amount_cents) * 1.0 / SUM(f.claim_amount_cents)) - c.target_discount_rate) >= 0.005
ORDER BY ABS(variance_to_target_points) DESC;
