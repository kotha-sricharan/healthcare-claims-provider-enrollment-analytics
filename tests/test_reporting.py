"""Unit tests proving reports are built from calculated inputs."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.reporting import generate_reports


class ReportingTests(unittest.TestCase):
    def test_report_generation_uses_calculated_data(self):
        generation = {"claim_rows": 3, "unique_claims": 2}
        etl = {
            "source_counts": {"claim_rows": 3}, "loaded_claims": 1, "quarantined_claims": 1,
            "quality": {
                "duplicate_claim_count": 1, "critical_error_count": 0,
                "issue_counts": {"INVALID_PROVIDER": 1},
            },
            "reconciliation": {
                "unique_claim_count": {"source": 2, "target": 2, "difference": 0, "status": "PASS"},
            },
        }
        claims = {
            "overall": {
                "claim_volume": 1, "members_with_claims": 1, "total_billed_amount": 100.0,
                "total_allowed_amount": 80.0, "total_paid_amount": 70.0,
                "denial_rejection_rate": 0.0, "denied_rejected_count": 0,
                "average_claim_value": 100.0, "average_processing_days": 2.0, "cost_spike_count": 0,
            },
            "monthly": [{
                "service_month": "2025-01", "claim_volume": 1, "unique_members": 1,
                "total_billed_amount": 100.0, "total_allowed_amount": 80.0,
                "total_paid_amount": 70.0, "denial_rejection_rate": 0.0,
                "average_claim_value": 100.0, "cost_spike_count": 0,
            }],
        }
        provider = {
            "provider_id": "P1", "provider_name": "Synthetic Provider", "provider_specialty": "Primary Care",
            "region": "NORTH", "contract_id": "K1", "contract_type": "FFS", "claim_volume": 1,
            "total_billed_amount": 100.0, "total_allowed_amount": 80.0, "total_paid_amount": 70.0,
            "denial_rejection_rate": 0.0, "actual_discount_rate": 20.0,
            "contract_target_discount_rate": 18.0, "discount_variance_points": 2.0,
            "average_paid_per_claim": 70.0, "cost_zscore": 0.0, "cost_outlier_flag": "N",
        }
        providers = {
            "providers": [provider], "specialties": [{"provider_specialty": "Primary Care", "total_paid_amount": 70.0}],
            "top_paid_provider": provider, "largest_discount_variance_provider": provider, "cost_outlier_count": 0,
        }
        month = {
            "reporting_month": "2025-01", "active_members": 1, "new_enrollments": 1,
            "terminations": 0, "utilizing_members": 1, "claim_volume": 1,
            "claims_per_1000_members": 1000.0, "paid_pmpm": 70.0,
        }
        enrollment = {"monthly": [month], "peak_enrollment": month, "peak_utilization": month}

        with tempfile.TemporaryDirectory() as directory, patch("src.reporting.OUTPUT_DIR", Path(directory)):
            paths = generate_reports(generation, etl, claims, providers, enrollment)
            report = (Path(directory) / "healthcare_business_report.md").read_text()
            quality = json.loads((Path(directory) / "data_quality_report.json").read_text())
            self.assertEqual(len(paths), 6)
            self.assertIn("$100.00 billed", report)
            self.assertIn("1 claims", report)
            self.assertEqual(quality["loaded_claims"], 1)


if __name__ == "__main__":
    unittest.main()
