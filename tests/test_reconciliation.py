"""Unit tests for source-to-target count and financial reconciliation."""
import unittest

from src.etl import reconcile_claims
from src.quality import DataQualityError


class ReconciliationTests(unittest.TestCase):
    def test_loaded_plus_quarantine_reconciles_to_unique_source(self):
        source = [
            {"claim_id": "C1", "claim_amount": "10.00", "allowed_amount": "8.00", "paid_amount": "7.00"},
            {"claim_id": "C2", "claim_amount": "20.00", "allowed_amount": "15.00", "paid_amount": "0.00"},
        ]
        loaded = [{"claim_id": "C1", "claim_amount_cents": 1000, "allowed_amount_cents": 800, "paid_amount_cents": 700}]
        quarantine = [{"claim_id": "C2", "claim_amount_cents": 2000, "allowed_amount_cents": 1500, "paid_amount_cents": 0}]
        result = reconcile_claims(source, loaded, quarantine)
        self.assertTrue(all(control["status"] == "PASS" for control in result.values()))
        self.assertEqual(result["unique_claim_count"]["difference"], 0)

    def test_amount_difference_fails_loudly(self):
        source = [{"claim_id": "C1", "claim_amount": "10.00", "allowed_amount": "8.00", "paid_amount": "7.00"}]
        loaded = [{"claim_id": "C1", "claim_amount_cents": 999, "allowed_amount_cents": 800, "paid_amount_cents": 700}]
        with self.assertRaises(DataQualityError):
            reconcile_claims(source, loaded, [])


if __name__ == "__main__":
    unittest.main()
