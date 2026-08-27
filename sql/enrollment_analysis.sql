-- Month-end membership, utilization, and paid PMPM trend.
WITH RECURSIVE months(month_start) AS (
    VALUES('2025-01-01')
    UNION ALL
    SELECT date(month_start, '+1 month') FROM months WHERE month_start < '2025-12-01'
), membership AS (
    SELECT m.month_start,
           COUNT(DISTINCT e.member_id) AS active_members
    FROM months m
    LEFT JOIN fact_enrollment e
      ON e.enrollment_start <= date(m.month_start, '+1 month', '-1 day')
     AND e.enrollment_end >= m.month_start
    GROUP BY m.month_start
), utilization AS (
    SELECT service_month, COUNT(*) AS claim_volume,
           COUNT(DISTINCT member_id) AS utilizing_members,
           SUM(paid_amount_cents) AS paid_cents
    FROM fact_claim GROUP BY service_month
)
SELECT substr(m.month_start,1,7) AS reporting_month, m.active_members,
       COALESCE(u.utilizing_members,0) AS utilizing_members,
       COALESCE(u.claim_volume,0) AS claim_volume,
       ROUND(1000.0 * COALESCE(u.claim_volume,0) / NULLIF(m.active_members,0), 2) AS claims_per_1000,
       ROUND(COALESCE(u.paid_cents,0) / 100.0 / NULLIF(m.active_members,0), 2) AS paid_pmpm,
       m.active_members - LAG(m.active_members) OVER (ORDER BY m.month_start) AS net_membership_change
FROM membership m
LEFT JOIN utilization u ON u.service_month = substr(m.month_start,1,7)
ORDER BY m.month_start;

-- Plan-level member, utilization, and financial comparison without fan-out joins.
WITH enrollment_counts AS (
    SELECT plan_id, COUNT(DISTINCT member_id) AS enrolled_members
    FROM fact_enrollment GROUP BY plan_id
), claim_counts AS (
    SELECT plan_id, COUNT(*) AS claim_volume,
           COUNT(DISTINCT member_id) AS utilizing_members,
           SUM(paid_amount_cents) AS paid_cents
    FROM fact_claim GROUP BY plan_id
)
SELECT p.plan_type, e.enrolled_members, c.utilizing_members, c.claim_volume,
       ROUND(c.paid_cents / 100.0, 2) AS paid_amount,
       ROUND(100.0 * c.utilizing_members / e.enrolled_members, 2) AS member_utilization_rate
FROM dim_plan p
JOIN enrollment_counts e ON e.plan_id = p.plan_id
JOIN claim_counts c ON c.plan_id = p.plan_id
ORDER BY paid_amount DESC;
