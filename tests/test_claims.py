"""Unit tests for claim transformation and calculated KPI logic."""
import sqlite3
import tempfile
import unittest
from pathlib import Path

from src.claims_analysis import calculate_claims_analytics
from src.etl import amount_to_cents, transform_claim


class ClaimsTests(unittest.TestCase):
    def test_currency_conversion_uses_integer_cents(self):
        self.assertEqual(amount_to_cents("19.995"), 2000)

    def test_transform_claim_creates_typed_fact_row(self):
        row = {
            "claim_id": "C1", "member_id": "M1", "provider_id": "P1", "contract_id": "K1",
            "plan_id": "PLN_PPO", "service_date": "2025-04-02", "claim_type": "PROFESSIONAL",
            "claim_amount": "125.10", "allowed_amount": "100.00", "paid_amount": "90.00",
            "claim_status": "PAID", "diagnosis_category": "Preventive", "source_system": "TEST",
            "processing_days": "4",
        }
        transformed = transform_claim(row, ["OUTSIDE_ENROLLMENT"])
        self.assertEqual(transformed["claim_amount_cents"], 12510)
        self.assertEqual(transformed["service_month"], "2025-04")
        self.assertEqual(transformed["processing_days"], 4)

    def test_calculated_claim_kpis(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "claims.db"
            connection = sqlite3.connect(database)
            connection.execute(
                """CREATE TABLE fact_claim (
                    claim_id TEXT, member_id TEXT, service_month TEXT, claim_type TEXT,
                    claim_amount_cents INTEGER, allowed_amount_cents INTEGER,
                    paid_amount_cents INTEGER, claim_status TEXT, processing_days INTEGER
                )"""
            )
            connection.executemany(
                "INSERT INTO fact_claim VALUES (?,?,?,?,?,?,?,?,?)",
                [
                    ("C1", "M1", "2025-01", "PROFESSIONAL", 10000, 8000, 7000, "PAID", 3),
                    ("C2", "M2", "2025-01", "INPATIENT", 6000000, 4500000, 0, "DENIED", 7),
                ],
            )
            connection.commit()
            connection.close()
            result = calculate_claims_analytics(database)
        self.assertEqual(result["overall"]["claim_volume"], 2)
        self.assertEqual(result["overall"]["total_paid_amount"], 70.0)
        self.assertEqual(result["overall"]["denial_rejection_rate"], 50.0)
        self.assertEqual(result["overall"]["cost_spike_count"], 1)


if __name__ == "__main__":
    unittest.main()
