"""Data-quality controls and healthcare business-rule validation."""
from __future__ import annotations

from collections import Counter
from datetime import date
from decimal import Decimal, InvalidOperation

from src.config import COST_SPIKE_THRESHOLD_CENTS


class DataQualityError(RuntimeError):
    """Raised when a critical source-control failure makes reporting unsafe."""


def find_duplicates(rows: list[dict], key: str) -> list[str]:
    """Return sorted nonblank identifiers appearing more than once."""
    counts = Counter(row.get(key, "") for row in rows if row.get(key, ""))
    return sorted(identifier for identifier, count in counts.items() if count > 1)


def _parse_amount(value: str, field: str, claim_id: str, critical: list[str]) -> Decimal | None:
    try:
        amount = Decimal(value)
    except (InvalidOperation, TypeError):
        critical.append(f"{claim_id}: {field} is not numeric")
        return None
    if amount < 0:
        critical.append(f"{claim_id}: {field} is negative")
        return None
    return amount


def _parse_date(value: str, field: str, identifier: str, critical: list[str]) -> date | None:
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        critical.append(f"{identifier}: {field} is not a valid ISO date")
        return None


def validate_reference_data(
    members: list[dict],
    providers: list[dict],
    contracts: list[dict],
    enrollment: list[dict],
    valid_plan_ids: set[str],
) -> None:
    """Fail on duplicate keys, broken reference chains, or invalid date ranges."""
    critical: list[str] = []
    for rows, key in (
        (members, "member_id"), (providers, "provider_id"),
        (contracts, "contract_id"), (enrollment, "enrollment_id"),
    ):
        duplicates = find_duplicates(rows, key)
        if duplicates:
            critical.append(f"Duplicate {key} values: {', '.join(duplicates[:5])}")

    member_ids = {row["member_id"] for row in members}
    contract_ids = {row["contract_id"] for row in contracts}
    for provider in providers:
        if provider.get("contract_id") not in contract_ids:
            critical.append(f"{provider.get('provider_id')}: invalid contract reference")
        if provider.get("provider_status") not in {"ACTIVE", "INACTIVE"}:
            critical.append(f"{provider.get('provider_id')}: invalid provider status")

    enrolled_members: set[str] = set()
    for row in enrollment:
        identifier = row.get("enrollment_id", "UNKNOWN_ENROLLMENT")
        if row.get("member_id") not in member_ids:
            critical.append(f"{identifier}: invalid member reference")
        if row.get("plan_id") not in valid_plan_ids:
            critical.append(f"{identifier}: invalid plan reference")
        start = _parse_date(row.get("enrollment_start", ""), "enrollment_start", identifier, critical)
        end = _parse_date(row.get("enrollment_end", ""), "enrollment_end", identifier, critical)
        if start and end and start > end:
            critical.append(f"{identifier}: enrollment start is after end")
        if row.get("member_id") in enrolled_members:
            critical.append(f"{identifier}: multiple source enrollment rows for member")
        enrolled_members.add(row.get("member_id", ""))

    missing_enrollment = member_ids - enrolled_members
    if missing_enrollment:
        critical.append(f"Members without enrollment: {len(missing_enrollment)}")
    if critical:
        raise DataQualityError("Critical reference-data validation failed:\n" + "\n".join(critical[:25]))


def validate_claims(
    claims: list[dict],
    members: list[dict],
    providers: list[dict],
    contracts: list[dict],
    enrollment: list[dict],
    raise_on_critical: bool = True,
) -> dict:
    """Classify claim-level issues and raise when integrity controls fail.

    Invalid providers and paid-over-allowed claims are quarantinable control
    exceptions. Unknown members, malformed values, invalid domains, and broken
    contract/plan relationships are critical because they make reconciliation
    or analytical attribution unreliable.
    """
    member_ids = {row["member_id"] for row in members}
    provider_by_id = {row["provider_id"]: row for row in providers}
    contract_ids = {row["contract_id"] for row in contracts}
    enrollment_by_member = {row["member_id"]: row for row in enrollment}
    duplicates = find_duplicates(claims, "claim_id")
    duplicate_set = set(duplicates)
    valid_statuses = {"PAID", "DENIED", "REJECTED", "PENDING"}
    valid_types = {"PROFESSIONAL", "OUTPATIENT", "INPATIENT", "PHARMACY"}
    critical: list[str] = []
    issues: list[dict] = []

    for duplicate_id in duplicates:
        issues.append({
            "claim_id": duplicate_id,
            "issue_type": "DUPLICATE_CLAIM",
            "severity": "MEDIUM",
            "action": "DEDUPLICATE",
        })

    seen: set[str] = set()
    for row in claims:
        claim_id = row.get("claim_id", "") or "MISSING_CLAIM_ID"
        if claim_id in seen:
            continue
        seen.add(claim_id)
        if not row.get("claim_id"):
            critical.append("A claim is missing claim_id")
            continue
        if row.get("member_id") not in member_ids:
            critical.append(f"{claim_id}: invalid member reference")
            continue
        member_enrollment = enrollment_by_member.get(row["member_id"])
        if member_enrollment is None:
            critical.append(f"{claim_id}: member has no enrollment")
            continue
        if row.get("plan_id") != member_enrollment.get("plan_id"):
            critical.append(f"{claim_id}: claim plan does not match enrollment")
        if row.get("contract_id") not in contract_ids:
            critical.append(f"{claim_id}: invalid contract reference")

        provider = provider_by_id.get(row.get("provider_id", ""))
        if provider is None:
            issues.append({"claim_id": claim_id, "issue_type": "INVALID_PROVIDER", "severity": "HIGH", "action": "QUARANTINE"})
        elif row.get("contract_id") != provider.get("contract_id"):
            critical.append(f"{claim_id}: provider contract mismatch")

        if row.get("claim_status") not in valid_statuses:
            critical.append(f"{claim_id}: invalid claim status")
        if row.get("claim_type") not in valid_types:
            critical.append(f"{claim_id}: invalid claim type")

        billed = _parse_amount(row.get("claim_amount", ""), "claim_amount", claim_id, critical)
        allowed = _parse_amount(row.get("allowed_amount", ""), "allowed_amount", claim_id, critical)
        paid = _parse_amount(row.get("paid_amount", ""), "paid_amount", claim_id, critical)
        if billed is not None and allowed is not None and allowed > billed:
            critical.append(f"{claim_id}: allowed amount exceeds billed amount")
        if paid is not None and allowed is not None and paid > allowed:
            issues.append({"claim_id": claim_id, "issue_type": "PAID_EXCEEDS_ALLOWED", "severity": "HIGH", "action": "QUARANTINE"})

        service_date = _parse_date(row.get("service_date", ""), "service_date", claim_id, critical)
        enrollment_start = date.fromisoformat(member_enrollment["enrollment_start"])
        enrollment_end = date.fromisoformat(member_enrollment["enrollment_end"])
        if service_date and not enrollment_start <= service_date <= enrollment_end:
            issues.append({"claim_id": claim_id, "issue_type": "OUTSIDE_ENROLLMENT", "severity": "HIGH", "action": "REVIEW"})
        if not row.get("diagnosis_category"):
            issues.append({"claim_id": claim_id, "issue_type": "MISSING_REQUIRED_FIELD", "severity": "MEDIUM", "action": "REVIEW"})
        if billed is not None and int(billed * 100) > COST_SPIKE_THRESHOLD_CENTS:
            issues.append({"claim_id": claim_id, "issue_type": "COST_SPIKE", "severity": "MEDIUM", "action": "REVIEW"})

    if critical and raise_on_critical:
        raise DataQualityError("Critical claim validation failed:\n" + "\n".join(critical[:25]))

    issue_counts = Counter(issue["issue_type"] for issue in issues)
    return {
        "rows_checked": len(claims),
        "unique_claims": len(seen),
        "duplicate_claim_ids": duplicates,
        "duplicate_claim_count": len(duplicates),
        "issues": issues,
        "issue_counts": dict(sorted(issue_counts.items())),
        "critical_errors": critical,
        "critical_error_count": len(critical),
        "quarantine_claim_ids": sorted({issue["claim_id"] for issue in issues if issue["action"] == "QUARANTINE"}),
        "duplicate_set": duplicate_set,
    }
