-- Monthly financial and denial trend used by the dashboard extract.
WITH monthly_claims AS (
    SELECT service_month,
           COUNT(*) AS claim_volume,
           SUM(claim_amount_cents) AS billed_cents,
           SUM(allowed_amount_cents) AS allowed_cents,
           SUM(paid_amount_cents) AS paid_cents,
           SUM(CASE WHEN claim_status IN ('DENIED','REJECTED') THEN 1 ELSE 0 END) AS denied_rejected
    FROM fact_claim
    GROUP BY service_month
)
SELECT service_month, claim_volume,
       ROUND(billed_cents / 100.0, 2) AS billed_amount,
       ROUND(allowed_cents / 100.0, 2) AS allowed_amount,
       ROUND(paid_cents / 100.0, 2) AS paid_amount,
       ROUND(100.0 * denied_rejected / claim_volume, 2) AS denial_rejection_rate,
       ROUND((paid_cents - LAG(paid_cents) OVER (ORDER BY service_month)) / 100.0, 2) AS paid_month_over_month_change
FROM monthly_claims
ORDER BY service_month;

-- Claim-type mix and contribution to total paid cost.
WITH type_summary AS (
    SELECT claim_type, COUNT(*) AS claim_volume,
           SUM(claim_amount_cents) AS billed_cents,
           SUM(paid_amount_cents) AS paid_cents
    FROM fact_claim
    GROUP BY claim_type
)
SELECT claim_type, claim_volume,
       ROUND(billed_cents / 100.0, 2) AS billed_amount,
       ROUND(paid_cents / 100.0, 2) AS paid_amount,
       ROUND(100.0 * paid_cents / SUM(paid_cents) OVER (), 2) AS percentage_of_paid_cost
FROM type_summary
ORDER BY paid_cents DESC;

-- Highest-cost claims for targeted utilization and contract review.
SELECT claim_id, provider_id, member_id, service_date, claim_type,
       ROUND(claim_amount_cents / 100.0, 2) AS billed_amount,
       ROUND(paid_amount_cents / 100.0, 2) AS paid_amount,
       ROW_NUMBER() OVER (ORDER BY claim_amount_cents DESC) AS cost_rank
FROM fact_claim
WHERE claim_amount_cents > 5000000
ORDER BY cost_rank;
