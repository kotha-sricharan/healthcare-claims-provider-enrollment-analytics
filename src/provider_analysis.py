"""Provider, specialty, contract, and statistical outlier analytics."""
from __future__ import annotations

import sqlite3
from statistics import mean, pstdev

from src.config import DATABASE_PATH


def _money(cents: int | float | None) -> float:
    return round((cents or 0) / 100, 2)


def calculate_provider_analytics(database_path=DATABASE_PATH) -> dict:
    """Return provider-level performance with z-score cost outlier flags."""
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    rows = connection.execute(
        """SELECT p.provider_id, p.provider_name, p.provider_specialty, p.region,
                  p.contract_id, c.contract_type, c.target_discount_rate,
                  COUNT(f.claim_id) AS claim_volume,
                  COALESCE(SUM(f.claim_amount_cents),0) AS billed_cents,
                  COALESCE(SUM(f.allowed_amount_cents),0) AS allowed_cents,
                  COALESCE(SUM(f.paid_amount_cents),0) AS paid_cents,
                  COALESCE(SUM(CASE WHEN f.claim_status IN ('DENIED','REJECTED') THEN 1 ELSE 0 END),0) AS denied_rejected
           FROM dim_provider p
           JOIN dim_contract c ON c.contract_id = p.contract_id
           LEFT JOIN fact_claim f ON f.provider_id = p.provider_id
           GROUP BY p.provider_id, p.provider_name, p.provider_specialty, p.region,
                    p.contract_id, c.contract_type, c.target_discount_rate
           ORDER BY p.provider_id"""
    ).fetchall()
    specialty_rows = connection.execute(
        """SELECT p.provider_specialty, COUNT(f.claim_id) AS claim_volume,
                  SUM(f.claim_amount_cents) AS billed_cents,
                  SUM(f.paid_amount_cents) AS paid_cents,
                  SUM(CASE WHEN f.claim_status IN ('DENIED','REJECTED') THEN 1 ELSE 0 END) AS denied_rejected
           FROM fact_claim f JOIN dim_provider p ON p.provider_id = f.provider_id
           GROUP BY p.provider_specialty ORDER BY paid_cents DESC"""
    ).fetchall()
    contract_rows = connection.execute(
        """SELECT c.contract_id, c.contract_type, c.target_discount_rate,
                  COUNT(f.claim_id) AS claim_volume,
                  SUM(f.claim_amount_cents) AS billed_cents,
                  SUM(f.allowed_amount_cents) AS allowed_cents,
                  SUM(f.paid_amount_cents) AS paid_cents
           FROM dim_contract c LEFT JOIN fact_claim f ON f.contract_id = c.contract_id
           GROUP BY c.contract_id, c.contract_type, c.target_discount_rate
           ORDER BY paid_cents DESC"""
    ).fetchall()
    connection.close()

    average_paid_values = [row["paid_cents"] / row["claim_volume"] for row in rows if row["claim_volume"]]
    cost_mean = mean(average_paid_values)
    cost_std = pstdev(average_paid_values) or 1
    providers = []
    for row in rows:
        volume = row["claim_volume"]
        actual_discount = 1 - row["allowed_cents"] / row["billed_cents"] if row["billed_cents"] else 0
        average_paid_cents = row["paid_cents"] / volume if volume else 0
        zscore = (average_paid_cents - cost_mean) / cost_std if volume else 0
        providers.append({
            "provider_id": row["provider_id"],
            "provider_name": row["provider_name"],
            "provider_specialty": row["provider_specialty"],
            "region": row["region"],
            "contract_id": row["contract_id"],
            "contract_type": row["contract_type"],
            "claim_volume": volume,
            "total_billed_amount": _money(row["billed_cents"]),
            "total_allowed_amount": _money(row["allowed_cents"]),
            "total_paid_amount": _money(row["paid_cents"]),
            "denial_rejection_rate": round(100 * row["denied_rejected"] / volume, 2) if volume else 0,
            "actual_discount_rate": round(100 * actual_discount, 2),
            "contract_target_discount_rate": round(100 * row["target_discount_rate"], 2),
            "discount_variance_points": round(100 * (actual_discount - row["target_discount_rate"]), 2),
            "average_paid_per_claim": _money(average_paid_cents),
            "cost_zscore": round(zscore, 2),
            "cost_outlier_flag": "Y" if abs(zscore) >= 2.5 else "N",
        })
    specialties = [
        {
            "provider_specialty": row["provider_specialty"],
            "claim_volume": row["claim_volume"],
            "total_billed_amount": _money(row["billed_cents"]),
            "total_paid_amount": _money(row["paid_cents"]),
            "denial_rejection_rate": round(100 * row["denied_rejected"] / row["claim_volume"], 2),
        }
        for row in specialty_rows
    ]
    contracts = []
    for row in contract_rows:
        actual_discount = 1 - row["allowed_cents"] / row["billed_cents"] if row["billed_cents"] else 0
        contracts.append({
            "contract_id": row["contract_id"], "contract_type": row["contract_type"],
            "claim_volume": row["claim_volume"], "total_paid_amount": _money(row["paid_cents"]),
            "actual_discount_rate": round(100 * actual_discount, 2),
            "target_discount_rate": round(100 * row["target_discount_rate"], 2),
            "discount_variance_points": round(100 * (actual_discount - row["target_discount_rate"]), 2),
        })
    top_paid = max(providers, key=lambda item: item["total_paid_amount"])
    largest_discount_variance = max(providers, key=lambda item: abs(item["discount_variance_points"]))
    return {
        "providers": providers,
        "specialties": specialties,
        "contracts": contracts,
        "top_paid_provider": top_paid,
        "largest_discount_variance_provider": largest_discount_variance,
        "cost_outlier_count": sum(item["cost_outlier_flag"] == "Y" for item in providers),
    }
