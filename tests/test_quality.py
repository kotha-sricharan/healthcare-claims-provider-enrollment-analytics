"""Unit tests for healthcare data-quality and eligibility controls."""
import unittest

from src.quality import DataQualityError, find_duplicates, validate_claims


def reference_rows():
    members = [{"member_id": "SYNM000001"}]
    providers = [{"provider_id": "PRV0001", "contract_id": "CTR001"}]
    contracts = [{"contract_id": "CTR001"}]
    enrollment = [{
        "member_id": "SYNM000001", "plan_id": "PLN_PPO",
        "enrollment_start": "2025-01-01", "enrollment_end": "2025-12-31",
    }]
    return members, providers, contracts, enrollment


def valid_claim():
    return {
        "claim_id": "CLM0000001", "member_id": "SYNM000001", "provider_id": "PRV0001",
        "contract_id": "CTR001", "plan_id": "PLN_PPO", "service_date": "2025-06-15",
        "claim_type": "PROFESSIONAL", "claim_amount": "100.00", "allowed_amount": "80.00",
        "paid_amount": "70.00", "claim_status": "PAID", "diagnosis_category": "Preventive",
    }


class QualityTests(unittest.TestCase):
    def test_duplicate_claim_detection(self):
        rows = [{"claim_id": "C1"}, {"claim_id": "C2"}, {"claim_id": "C1"}]
        self.assertEqual(find_duplicates(rows, "claim_id"), ["C1"])

    def test_invalid_member_is_critical(self):
        members, providers, contracts, enrollment = reference_rows()
        claim = valid_claim()
        claim["member_id"] = "UNKNOWN_MEMBER"
        with self.assertRaises(DataQualityError):
            validate_claims([claim], members, providers, contracts, enrollment)

    def test_invalid_provider_is_quarantined(self):
        members, providers, contracts, enrollment = reference_rows()
        claim = valid_claim()
        claim["provider_id"] = "UNKNOWN_PROVIDER"
        result = validate_claims([claim], members, providers, contracts, enrollment)
        self.assertEqual(result["issue_counts"]["INVALID_PROVIDER"], 1)
        self.assertEqual(result["quarantine_claim_ids"], ["CLM0000001"])

    def test_paid_greater_than_allowed_is_quarantined(self):
        members, providers, contracts, enrollment = reference_rows()
        claim = valid_claim()
        claim["paid_amount"] = "85.00"
        result = validate_claims([claim], members, providers, contracts, enrollment)
        self.assertEqual(result["issue_counts"]["PAID_EXCEEDS_ALLOWED"], 1)

    def test_outside_enrollment_is_detected(self):
        members, providers, contracts, enrollment = reference_rows()
        claim = valid_claim()
        claim["service_date"] = "2026-01-01"
        result = validate_claims([claim], members, providers, contracts, enrollment)
        self.assertEqual(result["issue_counts"]["OUTSIDE_ENROLLMENT"], 1)


if __name__ == "__main__":
    unittest.main()
