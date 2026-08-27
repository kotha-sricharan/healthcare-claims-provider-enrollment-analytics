"""Enrollment, membership, utilization, and paid-per-member analytics."""
from __future__ import annotations

import calendar
import sqlite3
from datetime import date

from src.config import DATABASE_PATH


def calculate_enrollment_analytics(database_path=DATABASE_PATH) -> dict:
    """Calculate month-end enrollment and utilization trends for calendar 2025."""
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    monthly = []
    for month in range(1, 13):
        month_start = date(2025, month, 1)
        month_end = date(2025, month, calendar.monthrange(2025, month)[1])
        period = month_start.strftime("%Y-%m")
        active_members = connection.execute(
            """SELECT COUNT(DISTINCT member_id) FROM fact_enrollment
               WHERE enrollment_start <= ? AND enrollment_end >= ?""",
            (month_end.isoformat(), month_start.isoformat()),
        ).fetchone()[0]
        new_enrollments = connection.execute(
            "SELECT COUNT(*) FROM fact_enrollment WHERE substr(enrollment_start,1,7) = ?", (period,)
        ).fetchone()[0]
        terminations = connection.execute(
            "SELECT COUNT(*) FROM fact_enrollment WHERE substr(enrollment_end,1,7) = ?", (period,)
        ).fetchone()[0]
        claim_row = connection.execute(
            """SELECT COUNT(*) AS claim_volume, COALESCE(SUM(paid_amount_cents),0) AS paid_cents,
                      COUNT(DISTINCT member_id) AS utilizing_members
               FROM fact_claim WHERE service_month = ?""",
            (period,),
        ).fetchone()
        monthly.append({
            "reporting_month": period,
            "active_members": active_members,
            "new_enrollments": new_enrollments,
            "terminations": terminations,
            "utilizing_members": claim_row["utilizing_members"],
            "claim_volume": claim_row["claim_volume"],
            "claims_per_1000_members": round(1000 * claim_row["claim_volume"] / active_members, 2) if active_members else 0,
            "paid_pmpm": round(claim_row["paid_cents"] / 100 / active_members, 2) if active_members else 0,
        })
    plan_rows = connection.execute(
        """WITH enrollment_counts AS (
               SELECT plan_id, COUNT(DISTINCT member_id) AS members
               FROM fact_enrollment GROUP BY plan_id
           ), claim_counts AS (
               SELECT plan_id, COUNT(*) AS claim_volume,
                      SUM(paid_amount_cents) AS paid_cents
               FROM fact_claim GROUP BY plan_id
           )
           SELECT p.plan_type, COALESCE(e.members,0) AS members,
                  COALESCE(c.claim_volume,0) AS claim_volume,
                  COALESCE(c.paid_cents,0) AS paid_cents
           FROM dim_plan p
           LEFT JOIN enrollment_counts e ON e.plan_id = p.plan_id
           LEFT JOIN claim_counts c ON c.plan_id = p.plan_id
           ORDER BY members DESC"""
    ).fetchall()
    connection.close()
    plans = [
        {
            "plan_type": row["plan_type"], "enrolled_members": row["members"],
            "claim_volume": row["claim_volume"], "total_paid_amount": round(row["paid_cents"] / 100, 2),
        }
        for row in plan_rows
    ]
    peak_utilization = max(monthly, key=lambda item: item["claims_per_1000_members"])
    peak_enrollment = max(monthly, key=lambda item: item["active_members"])
    return {"monthly": monthly, "by_plan": plans, "peak_utilization": peak_utilization, "peak_enrollment": peak_enrollment}
