"""Validate, transform, reconcile, and load synthetic healthcare sources."""
from __future__ import annotations

import csv
import sqlite3
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

from src.config import DATABASE_PATH, PLANS, RAW_DIR, SQL_DIR, ensure_directories
from src.quality import DataQualityError, validate_claims, validate_reference_data


def read_csv(path: Path) -> list[dict]:
    """Read a UTF-8 CSV source into dictionaries."""
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def amount_to_cents(value: str | Decimal) -> int:
    """Convert a decimal currency value to exact integer cents."""
    return int((Decimal(value) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def transform_claim(row: dict, quality_flags: list[str] | None = None) -> dict:
    """Convert one validated source claim to the fact-table contract."""
    return {
        "claim_id": row["claim_id"],
        "member_id": row["member_id"],
        "provider_id": row["provider_id"],
        "contract_id": row["contract_id"],
        "plan_id": row["plan_id"],
        "service_date": row["service_date"],
        "service_month": row["service_date"][:7],
        "claim_type": row["claim_type"],
        "claim_amount_cents": amount_to_cents(row["claim_amount"]),
        "allowed_amount_cents": amount_to_cents(row["allowed_amount"]),
        "paid_amount_cents": amount_to_cents(row["paid_amount"]),
        "claim_status": row["claim_status"],
        "diagnosis_category": row.get("diagnosis_category") or None,
        "source_system": row["source_system"],
        "processing_days": int(row["processing_days"]) if row.get("processing_days") else None,
        "quality_flag": "|".join(sorted(quality_flags or [])) or "PASS",
    }


def reconcile_claims(unique_source: list[dict], loaded: list[dict], quarantined: list[dict]) -> dict:
    """Prove count and amount conservation across loaded and quarantined claims."""
    fields = {
        "claim_amount_cents": "claim_amount",
        "allowed_amount_cents": "allowed_amount",
        "paid_amount_cents": "paid_amount",
    }
    controls = {
        "unique_claim_count": {
            "source": len(unique_source),
            "target": len(loaded) + len(quarantined),
        }
    }
    for target_field, source_field in fields.items():
        controls[target_field] = {
            "source": sum(amount_to_cents(row[source_field]) for row in unique_source),
            "target": sum(row[target_field] for row in loaded) + sum(row[target_field] for row in quarantined),
        }
    for control in controls.values():
        control["difference"] = control["source"] - control["target"]
        control["status"] = "PASS" if control["difference"] == 0 else "FAIL"
    if any(control["status"] == "FAIL" for control in controls.values()):
        raise DataQualityError("Critical source-to-target reconciliation failed")
    return controls


def _load_database(
    members: list[dict], providers: list[dict], contracts: list[dict], enrollment: list[dict],
    claims: list[dict], quarantined: list[dict], issues: list[dict], controls: dict,
) -> None:
    if DATABASE_PATH.exists():
        DATABASE_PATH.unlink()
    connection = sqlite3.connect(DATABASE_PATH)
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        connection.executescript((SQL_DIR / "schema.sql").read_text(encoding="utf-8"))
        connection.executemany(
            "INSERT INTO dim_plan VALUES (:plan_id, :plan_type, :metal_level)", PLANS,
        )
        connection.executemany(
            "INSERT INTO dim_contract VALUES (:contract_id, :contract_name, :contract_type, :effective_start, :effective_end, :target_discount_rate, :quality_target, :active_flag)",
            contracts,
        )
        connection.executemany(
            "INSERT INTO dim_member VALUES (:member_id, :age_band, :risk_segment, :region, :member_status)", members,
        )
        connection.executemany(
            "INSERT INTO dim_provider VALUES (:provider_id, :provider_name, :provider_specialty, :region, :contract_id, :provider_status)", providers,
        )
        connection.executemany(
            "INSERT INTO fact_enrollment VALUES (:enrollment_id, :member_id, :plan_id, :enrollment_start, :enrollment_end, :coverage_status)", enrollment,
        )
        connection.executemany(
            """INSERT INTO fact_claim VALUES (
                :claim_id, :member_id, :provider_id, :contract_id, :plan_id,
                :service_date, :service_month, :claim_type, :claim_amount_cents,
                :allowed_amount_cents, :paid_amount_cents, :claim_status,
                :diagnosis_category, :source_system, :processing_days, :quality_flag
            )""",
            claims,
        )
        connection.executemany(
            """INSERT INTO claim_quarantine VALUES (
                :claim_id, :member_id, :source_provider_id, :contract_id,
                :service_date, :claim_amount_cents, :allowed_amount_cents,
                :paid_amount_cents, :quarantine_reason
            )""",
            quarantined,
        )
        exception_rows = [dict(exception_id=f"DQ{index:05d}", **issue) for index, issue in enumerate(issues, 1)]
        connection.executemany(
            "INSERT INTO claim_quality_exception VALUES (:exception_id, :claim_id, :issue_type, :severity, :action)",
            exception_rows,
        )
        control_rows = [
            {
                "control_name": name,
                "source_value": values["source"],
                "target_value": values["target"],
                "difference": values["difference"],
                "status": values["status"],
            }
            for name, values in controls.items()
        ]
        connection.executemany(
            "INSERT INTO etl_control VALUES (:control_name, :source_value, :target_value, :difference, :status)",
            control_rows,
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def run_etl() -> dict:
    """Execute source validation, typed transformation, reconciliation, and load."""
    ensure_directories()
    members = read_csv(RAW_DIR / "members.csv")
    providers = read_csv(RAW_DIR / "providers.csv")
    contracts = read_csv(RAW_DIR / "contracts.csv")
    enrollment = read_csv(RAW_DIR / "enrollment.csv")
    source_claims = read_csv(RAW_DIR / "claims.csv")

    validate_reference_data(members, providers, contracts, enrollment, {plan["plan_id"] for plan in PLANS})
    quality = validate_claims(source_claims, members, providers, contracts, enrollment)
    issue_map: dict[str, list[str]] = defaultdict(list)
    for issue in quality["issues"]:
        issue_map[issue["claim_id"]].append(issue["issue_type"])
    quarantine_ids = set(quality["quarantine_claim_ids"])

    unique_source: list[dict] = []
    seen: set[str] = set()
    for row in source_claims:
        if row["claim_id"] not in seen:
            unique_source.append(row)
            seen.add(row["claim_id"])

    loaded: list[dict] = []
    quarantined: list[dict] = []
    for row in unique_source:
        claim_id = row["claim_id"]
        if claim_id in quarantine_ids:
            quarantined.append({
                "claim_id": claim_id,
                "member_id": row["member_id"],
                "source_provider_id": row["provider_id"],
                "contract_id": row["contract_id"],
                "service_date": row["service_date"],
                "claim_amount_cents": amount_to_cents(row["claim_amount"]),
                "allowed_amount_cents": amount_to_cents(row["allowed_amount"]),
                "paid_amount_cents": amount_to_cents(row["paid_amount"]),
                "quarantine_reason": "|".join(sorted(issue_map[claim_id])),
            })
        else:
            loaded.append(transform_claim(row, issue_map[claim_id]))

    controls = reconcile_claims(unique_source, loaded, quarantined)
    _load_database(members, providers, contracts, enrollment, loaded, quarantined, quality["issues"], controls)

    public_quality = {key: value for key, value in quality.items() if key not in {"issues", "duplicate_set"}}
    return {
        "source_counts": {
            "members": len(members), "providers": len(providers), "contracts": len(contracts),
            "enrollment": len(enrollment), "claim_rows": len(source_claims),
            "unique_claims": len(unique_source),
        },
        "loaded_claims": len(loaded),
        "quarantined_claims": len(quarantined),
        "quality": public_quality,
        "quality_issues": quality["issues"],
        "reconciliation": controls,
        "database_path": str(DATABASE_PATH),
    }
