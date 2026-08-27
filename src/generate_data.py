"""Generate reproducible, fictional healthcare source files with controlled issues."""
from __future__ import annotations

import csv
import math
import random
from datetime import date, timedelta
from pathlib import Path
from typing import Iterable

from src.config import (
    CLAIM_COUNT,
    CONTRACT_COUNT,
    MEMBER_COUNT,
    PLANS,
    PROVIDER_COUNT,
    RANDOM_SEED,
    RAW_DIR,
    ensure_directories,
)

SPECIALTIES = (
    "Primary Care", "Cardiology", "Orthopedics", "Behavioral Health",
    "Radiology", "Emergency Medicine", "Oncology", "Pediatrics",
    "Dermatology", "General Surgery",
)
REGIONS = ("NORTH", "SOUTH", "EAST", "WEST")
CLAIM_TYPES = ("PROFESSIONAL", "OUTPATIENT", "INPATIENT", "PHARMACY")
CLAIM_STATUSES = ("PAID", "DENIED", "REJECTED", "PENDING")
DIAGNOSIS_CATEGORIES = (
    "Preventive", "Cardiovascular", "Musculoskeletal", "Respiratory",
    "Behavioral", "Digestive", "Endocrine", "Injury", "Oncology",
)


def _write_csv(path: Path, rows: Iterable[dict], fieldnames: list[str]) -> None:
    """Write a stable CSV using an explicit column order."""
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _random_date(rng: random.Random, start: date, end: date) -> date:
    """Return a uniformly distributed date within an inclusive range."""
    return start + timedelta(days=rng.randint(0, (end - start).days))


def _generate_contracts(rng: random.Random) -> list[dict]:
    contracts = []
    for number in range(1, CONTRACT_COUNT + 1):
        contracts.append({
            "contract_id": f"CTR{number:03d}",
            "contract_name": f"Synthetic Provider Contract {number:03d}",
            "contract_type": rng.choice(("FFS", "VALUE_BASED", "SHARED_SAVINGS")),
            "effective_start": "2024-01-01",
            "effective_end": "2026-12-31",
            "target_discount_rate": f"{rng.uniform(0.15, 0.34):.4f}",
            "quality_target": f"{rng.uniform(0.82, 0.96):.4f}",
            "active_flag": "Y",
        })
    return contracts


def _generate_providers(rng: random.Random, contracts: list[dict]) -> list[dict]:
    providers = []
    for number in range(1, PROVIDER_COUNT + 1):
        providers.append({
            "provider_id": f"PRV{number:04d}",
            "provider_name": f"Synthetic Provider Organization {number:03d}",
            "provider_specialty": rng.choice(SPECIALTIES),
            "region": rng.choice(REGIONS),
            "contract_id": rng.choice(contracts)["contract_id"],
            "provider_status": "ACTIVE" if rng.random() > 0.04 else "INACTIVE",
        })
    return providers


def _generate_members_and_enrollment(rng: random.Random) -> tuple[list[dict], list[dict]]:
    members: list[dict] = []
    enrollment: list[dict] = []
    for number in range(1, MEMBER_COUNT + 1):
        member_id = f"SYNM{number:06d}"
        plan = rng.choice(PLANS)
        start = _random_date(rng, date(2024, 7, 1), date(2025, 9, 15))
        if rng.random() < 0.32:
            earliest_end = max(start + timedelta(days=90), date(2025, 3, 31))
            end = _random_date(rng, earliest_end, date(2025, 12, 31))
        else:
            end = date(2026, 12, 31)
        members.append({
            "member_id": member_id,
            "age_band": rng.choice(("0-17", "18-34", "35-49", "50-64", "65+")),
            "risk_segment": rng.choices(("LOW", "MEDIUM", "HIGH"), weights=(55, 32, 13))[0],
            "region": rng.choice(REGIONS),
            "member_status": "TERMINATED" if end <= date(2025, 12, 31) else "ACTIVE",
        })
        enrollment.append({
            "enrollment_id": f"ENR{number:06d}",
            "member_id": member_id,
            "plan_id": plan["plan_id"],
            "plan_type": plan["plan_type"],
            "enrollment_start": start.isoformat(),
            "enrollment_end": end.isoformat(),
            "coverage_status": "TERMINATED" if end <= date(2025, 12, 31) else "ACTIVE",
        })
    return members, enrollment


def _base_claim_amount(rng: random.Random, claim_type: str) -> float:
    parameters = {
        "PROFESSIONAL": (math.log(550), 0.75, 12_000),
        "OUTPATIENT": (math.log(2_100), 0.75, 22_000),
        "INPATIENT": (math.log(13_500), 0.55, 32_000),
        "PHARMACY": (math.log(180), 0.85, 5_000),
    }
    mean, sigma, ceiling = parameters[claim_type]
    return round(max(25.0, min(rng.lognormvariate(mean, sigma), ceiling)), 2)


def _outside_coverage_date(enrollment: dict) -> date:
    start = date.fromisoformat(enrollment["enrollment_start"])
    end = date.fromisoformat(enrollment["enrollment_end"])
    if start > date(2025, 1, 1):
        return max(date(2025, 1, 1), start - timedelta(days=15))
    return min(date(2025, 12, 31), end + timedelta(days=15))


def _generate_claims(
    rng: random.Random,
    providers: list[dict],
    contracts: list[dict],
    enrollment: list[dict],
) -> tuple[list[dict], dict[str, int]]:
    contract_by_id = {row["contract_id"]: row for row in contracts}
    limited_enrollment = [
        row for row in enrollment
        if row["enrollment_start"] > "2025-01-01" or row["enrollment_end"] < "2025-12-31"
    ]
    indexes = list(range(CLAIM_COUNT))
    rng.shuffle(indexes)
    invalid_provider = set(indexes[:12])
    outside_enrollment = set(indexes[12:27])
    paid_over_allowed = set(indexes[27:37])
    missing_required = set(indexes[37:47])
    cost_spikes = set(indexes[47:65])

    rows: list[dict] = []
    for index in range(CLAIM_COUNT):
        member_enrollment = rng.choice(limited_enrollment if index in outside_enrollment else enrollment)
        provider = rng.choice(providers)
        contract = contract_by_id[provider["contract_id"]]
        coverage_start = max(date.fromisoformat(member_enrollment["enrollment_start"]), date(2025, 1, 1))
        coverage_end = min(date.fromisoformat(member_enrollment["enrollment_end"]), date(2025, 12, 31))
        service_date = _random_date(rng, coverage_start, coverage_end)
        if index in outside_enrollment:
            service_date = _outside_coverage_date(member_enrollment)

        claim_type = rng.choices(CLAIM_TYPES, weights=(49, 25, 9, 17))[0]
        billed = _base_claim_amount(rng, claim_type)
        if index in cost_spikes:
            billed = round(rng.uniform(80_000, 225_000), 2)
        target_discount = float(contract["target_discount_rate"])
        discount = min(0.46, max(0.08, target_discount + rng.uniform(-0.07, 0.07)))
        allowed = round(billed * (1 - discount), 2)
        status = rng.choices(CLAIM_STATUSES, weights=(82, 8, 4, 6))[0]
        paid = round(allowed * rng.uniform(0.82, 1.0), 2) if status == "PAID" else 0.0
        if index in paid_over_allowed:
            status = "PAID"
            paid = round(allowed + rng.uniform(25, 450), 2)

        rows.append({
            "claim_id": f"CLM{index + 1:07d}",
            "member_id": member_enrollment["member_id"],
            "provider_id": f"PRV_INVALID_{index + 1:03d}" if index in invalid_provider else provider["provider_id"],
            "contract_id": provider["contract_id"],
            "plan_id": member_enrollment["plan_id"],
            "service_date": service_date.isoformat(),
            "claim_type": claim_type,
            "claim_amount": f"{billed:.2f}",
            "allowed_amount": f"{allowed:.2f}",
            "paid_amount": f"{paid:.2f}",
            "claim_status": status,
            "diagnosis_category": "" if index in missing_required else rng.choice(DIAGNOSIS_CATEGORIES),
            "source_system": "SYNTHETIC_CLAIMS_ADJUDICATION",
            "processing_days": "" if status == "PENDING" else str(rng.randint(0, 21)),
        })

    for duplicate_index in sorted(rng.sample(range(CLAIM_COUNT), 8)):
        rows.append(dict(rows[duplicate_index]))

    return rows, {
        "duplicate_claim_rows": 8,
        "invalid_provider_claims": len(invalid_provider),
        "outside_enrollment_claims": len(outside_enrollment),
        "paid_over_allowed_claims": len(paid_over_allowed),
        "missing_required_claims": len(missing_required),
        "cost_spike_claims": len(cost_spikes),
    }


def generate_synthetic_data() -> dict[str, int]:
    """Generate all synthetic CSV sources and return reproducibility metadata."""
    ensure_directories()
    rng = random.Random(RANDOM_SEED)
    contracts = _generate_contracts(rng)
    providers = _generate_providers(rng, contracts)
    members, enrollment = _generate_members_and_enrollment(rng)
    claims, anomalies = _generate_claims(rng, providers, contracts, enrollment)

    _write_csv(RAW_DIR / "members.csv", members, list(members[0]))
    _write_csv(RAW_DIR / "providers.csv", providers, list(providers[0]))
    _write_csv(RAW_DIR / "contracts.csv", contracts, list(contracts[0]))
    _write_csv(RAW_DIR / "enrollment.csv", enrollment, list(enrollment[0]))
    _write_csv(RAW_DIR / "claims.csv", claims, list(claims[0]))

    return {
        "seed": RANDOM_SEED,
        "members": len(members),
        "providers": len(providers),
        "contracts": len(contracts),
        "enrollment_rows": len(enrollment),
        "unique_claims": CLAIM_COUNT,
        "claim_rows": len(claims),
        **anomalies,
    }


if __name__ == "__main__":
    print(generate_synthetic_data())
