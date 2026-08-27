"""Claims financial, utilization, denial, and cost-trend analytics."""
from __future__ import annotations

import sqlite3

from src.config import COST_SPIKE_THRESHOLD_CENTS, DATABASE_PATH


def _money(cents: int | float | None) -> float:
    return round((cents or 0) / 100, 2)


def calculate_claims_analytics(database_path=DATABASE_PATH) -> dict:
    """Calculate overall and monthly claims KPIs from loaded analytical facts."""
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    overall = connection.execute(
        """SELECT COUNT(*) AS claim_volume,
                  COUNT(DISTINCT member_id) AS members_with_claims,
                  SUM(claim_amount_cents) AS billed_cents,
                  SUM(allowed_amount_cents) AS allowed_cents,
                  SUM(paid_amount_cents) AS paid_cents,
                  SUM(CASE WHEN claim_status IN ('DENIED','REJECTED') THEN 1 ELSE 0 END) AS denied_rejected,
                  AVG(claim_amount_cents) AS average_claim_cents,
                  AVG(CASE WHEN processing_days IS NOT NULL THEN processing_days END) AS average_processing_days,
                  SUM(CASE WHEN claim_amount_cents > ? THEN 1 ELSE 0 END) AS cost_spike_count
           FROM fact_claim""",
        (COST_SPIKE_THRESHOLD_CENTS,),
    ).fetchone()
    monthly_rows = connection.execute(
        """SELECT service_month,
                  COUNT(*) AS claim_volume,
                  COUNT(DISTINCT member_id) AS unique_members,
                  SUM(claim_amount_cents) AS billed_cents,
                  SUM(allowed_amount_cents) AS allowed_cents,
                  SUM(paid_amount_cents) AS paid_cents,
                  SUM(CASE WHEN claim_status IN ('DENIED','REJECTED') THEN 1 ELSE 0 END) AS denied_rejected,
                  AVG(claim_amount_cents) AS average_claim_cents,
                  SUM(CASE WHEN claim_amount_cents > ? THEN 1 ELSE 0 END) AS cost_spike_count
           FROM fact_claim
           GROUP BY service_month
           ORDER BY service_month""",
        (COST_SPIKE_THRESHOLD_CENTS,),
    ).fetchall()
    type_rows = connection.execute(
        """SELECT claim_type, COUNT(*) AS claim_volume,
                  SUM(claim_amount_cents) AS billed_cents,
                  SUM(paid_amount_cents) AS paid_cents
           FROM fact_claim GROUP BY claim_type ORDER BY paid_cents DESC"""
    ).fetchall()
    connection.close()

    claim_volume = overall["claim_volume"]
    overall_result = {
        "claim_volume": claim_volume,
        "members_with_claims": overall["members_with_claims"],
        "total_billed_amount": _money(overall["billed_cents"]),
        "total_allowed_amount": _money(overall["allowed_cents"]),
        "total_paid_amount": _money(overall["paid_cents"]),
        "denied_rejected_count": overall["denied_rejected"],
        "denial_rejection_rate": round(100 * overall["denied_rejected"] / claim_volume, 2) if claim_volume else 0,
        "average_claim_value": _money(overall["average_claim_cents"]),
        "average_processing_days": round(overall["average_processing_days"] or 0, 2),
        "cost_spike_count": overall["cost_spike_count"],
        "allowed_to_billed_rate": round(100 * overall["allowed_cents"] / overall["billed_cents"], 2),
        "paid_to_allowed_rate": round(100 * overall["paid_cents"] / overall["allowed_cents"], 2),
    }
    monthly = []
    for row in monthly_rows:
        monthly.append({
            "service_month": row["service_month"],
            "claim_volume": row["claim_volume"],
            "unique_members": row["unique_members"],
            "total_billed_amount": _money(row["billed_cents"]),
            "total_allowed_amount": _money(row["allowed_cents"]),
            "total_paid_amount": _money(row["paid_cents"]),
            "denial_rejection_rate": round(100 * row["denied_rejected"] / row["claim_volume"], 2),
            "average_claim_value": _money(row["average_claim_cents"]),
            "cost_spike_count": row["cost_spike_count"],
        })
    by_type = [
        {
            "claim_type": row["claim_type"], "claim_volume": row["claim_volume"],
            "total_billed_amount": _money(row["billed_cents"]),
            "total_paid_amount": _money(row["paid_cents"]),
        }
        for row in type_rows
    ]
    return {"overall": overall_result, "monthly": monthly, "by_claim_type": by_type}
