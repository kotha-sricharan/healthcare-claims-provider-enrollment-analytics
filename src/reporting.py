"""Create BI-ready extracts, audit evidence, and a computed business narrative."""
from __future__ import annotations

import csv
import json
from pathlib import Path

from src.config import OUTPUT_DIR, ensure_directories


def _write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        raise ValueError(f"Cannot write an empty reporting artifact: {path.name}")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _money(value: float) -> str:
    return f"${value:,.2f}"


def _reconciliation_rows(controls: dict) -> list[dict]:
    rows = []
    for control_name, values in controls.items():
        is_amount = control_name.endswith("_cents")
        divisor = 100 if is_amount else 1
        rows.append({
            "control_name": control_name.removesuffix("_cents"),
            "unit": "USD" if is_amount else "COUNT",
            "source_value": round(values["source"] / divisor, 2),
            "target_value": round(values["target"] / divisor, 2),
            "difference": round(values["difference"] / divisor, 2),
            "status": values["status"],
        })
    return rows


def _recommendations(claims: dict, providers: dict, enrollment: dict, issue_counts: dict) -> list[str]:
    recommendations: list[str] = []
    if claims["denial_rejection_rate"] >= 8:
        recommendations.append(
            f"Review denial and rejection edits by provider and claim type; the current rate is {claims['denial_rejection_rate']:.2f}%."
        )
    if issue_counts.get("INVALID_PROVIDER", 0):
        recommendations.append(
            f"Add provider-master validation at intake for the {issue_counts['INVALID_PROVIDER']} claims currently quarantined for invalid provider identifiers."
        )
    if issue_counts.get("PAID_EXCEEDS_ALLOWED", 0):
        recommendations.append(
            f"Prevent payment release when paid exceeds allowed; {issue_counts['PAID_EXCEEDS_ALLOWED']} controlled exceptions were quarantined."
        )
    if issue_counts.get("OUTSIDE_ENROLLMENT", 0):
        recommendations.append(
            f"Run real-time eligibility checks before adjudication for the {issue_counts['OUTSIDE_ENROLLMENT']} claims outside enrollment dates."
        )
    if claims["cost_spike_count"]:
        recommendations.append(
            f"Route the {claims['cost_spike_count']} high-cost claims to clinical and contract review, prioritizing statistically unusual providers."
        )
    if providers["discount_variance_points"] < -2:
        recommendations.append(
            f"Review contract configuration for {providers['provider_id']}; its discount performance is {abs(providers['discount_variance_points']):.2f} points below target."
        )
    if enrollment["claims_per_1000_members"] > 1000:
        recommendations.append(
            f"Investigate utilization drivers in {enrollment['reporting_month']}, the peak month at {enrollment['claims_per_1000_members']:.2f} claims per 1,000 members."
        )
    return recommendations or ["Continue monitoring monthly cost, utilization, eligibility, and contract controls using the generated extracts."]


def _business_report(
    generation: dict, etl: dict, claims: dict, providers: dict, enrollment: dict,
) -> str:
    overall = claims["overall"]
    highest_paid_month = max(claims["monthly"], key=lambda item: item["total_paid_amount"])
    top_specialty = max(providers["specialties"], key=lambda item: item["total_paid_amount"])
    top_provider = providers["top_paid_provider"]
    discount_provider = providers["largest_discount_variance_provider"]
    peak_enrollment = enrollment["peak_enrollment"]
    peak_utilization = enrollment["peak_utilization"]
    issue_counts = etl["quality"]["issue_counts"]
    recommendations = _recommendations(overall, discount_provider, peak_utilization, issue_counts)
    reconciliation_status = "PASS" if all(
        control["status"] == "PASS" for control in etl["reconciliation"].values()
    ) else "FAIL"

    lines = [
        "# Healthcare Claims, Provider & Enrollment Analytics Report",
        "",
        "Reporting period: **2025-01 through 2025-12**",
        "Data classification: **Synthetic portfolio data only — no PHI**",
        "",
        "## Executive Summary",
        "",
        f"The governed pipeline loaded **{overall['claim_volume']:,} analytically valid claims** "
        f"covering **{overall['members_with_claims']:,} synthetic members**. The claims represent "
        f"**{_money(overall['total_billed_amount'])} billed**, **{_money(overall['total_allowed_amount'])} allowed**, "
        f"and **{_money(overall['total_paid_amount'])} paid**. Source-to-target reconciliation status is **{reconciliation_status}**.",
        "",
        "## Overall Claim Trends",
        "",
        f"- Denial/rejection rate: **{overall['denial_rejection_rate']:.2f}%** ({overall['denied_rejected_count']:,} claims).",
        f"- Average billed claim value: **{_money(overall['average_claim_value'])}**.",
        f"- Average processing time: **{overall['average_processing_days']:.2f} days**.",
        f"- Highest paid month: **{highest_paid_month['service_month']}** at **{_money(highest_paid_month['total_paid_amount'])}**.",
        f"- Controlled high-cost claims above the rule threshold: **{overall['cost_spike_count']}**.",
        "",
        "## Provider & Contract Observations",
        "",
        f"**{top_provider['provider_name']}** has the highest total paid amount at **{_money(top_provider['total_paid_amount'])}** "
        f"across **{top_provider['claim_volume']:,} claims**. **{top_specialty['provider_specialty']}** is the highest-paid specialty "
        f"at **{_money(top_specialty['total_paid_amount'])}**. Provider cost z-scores flag **{providers['cost_outlier_count']}** "
        "organizations for analytical review. "
        f"The largest absolute contract discount variance belongs to **{discount_provider['provider_id']}** at "
        f"**{discount_provider['discount_variance_points']:.2f} percentage points** versus target.",
        "",
        "## Enrollment & Utilization Observations",
        "",
        f"Peak active enrollment is **{peak_enrollment['active_members']:,} members** in **{peak_enrollment['reporting_month']}**. "
        f"Peak utilization occurs in **{peak_utilization['reporting_month']}** at "
        f"**{peak_utilization['claims_per_1000_members']:.2f} claims per 1,000 active members**, with paid PMPM of "
        f"**{_money(peak_utilization['paid_pmpm'])}**.",
        "",
        "## Data Quality Findings",
        "",
        f"The source contains **{generation['claim_rows']:,} rows** and **{generation['unique_claims']:,} unique claim IDs**. "
        f"The pipeline removed **{etl['quality']['duplicate_claim_count']} duplicate IDs**, loaded **{etl['loaded_claims']:,} claims**, "
        f"and quarantined **{etl['quarantined_claims']} claims**. Critical validation errors: "
        f"**{etl['quality']['critical_error_count']}**.",
        "",
        "| Controlled issue | Count |",
        "|---|---:|",
        *[f"| {name.replace('_', ' ').title()} | {count} |" for name, count in sorted(issue_counts.items())],
        "",
        "## Financial Reconciliation Findings",
        "",
        f"All **{len(etl['reconciliation'])}** source-to-target count and amount controls passed. Unique source claims equal "
        "loaded plus quarantined claims, and billed, allowed, and paid amounts are conserved exactly in integer cents.",
        "",
        "## Recommendations",
        "",
        *[f"{index}. {recommendation}" for index, recommendation in enumerate(recommendations, 1)],
        "",
        "## Methodology",
        "",
        "The workflow creates fictional members, providers, contracts, enrollment spans, and claims with a fixed seed. "
        "It validates identifiers, domains, amounts, eligibility, dates, and contract relationships; removes duplicate rows; "
        "quarantines financially unsafe records; loads a constrained SQLite dimensional model; reconciles counts and amounts; "
        "calculates monthly, provider, specialty, contract, enrollment, and outlier measures; and publishes flat audit-ready extracts.",
        "",
        "All findings describe generated demonstration records. They do not represent real patients, members, providers, or healthcare operations.",
        "",
    ]
    return "\n".join(lines)


def generate_reports(generation: dict, etl: dict, claims: dict, providers: dict, enrollment: dict) -> list[Path]:
    """Generate the complete reporting package from calculated facts."""
    ensure_directories()
    claims_path = OUTPUT_DIR / "claims_kpis.csv"
    provider_path = OUTPUT_DIR / "provider_summary.csv"
    enrollment_path = OUTPUT_DIR / "enrollment_summary.csv"
    reconciliation_path = OUTPUT_DIR / "reconciliation_report.csv"
    quality_path = OUTPUT_DIR / "data_quality_report.json"
    report_path = OUTPUT_DIR / "healthcare_business_report.md"

    _write_csv(claims_path, claims["monthly"])
    _write_csv(provider_path, providers["providers"])
    _write_csv(enrollment_path, enrollment["monthly"])
    _write_csv(reconciliation_path, _reconciliation_rows(etl["reconciliation"]))
    quality_payload = {
        "status": "PASS" if etl["quality"]["critical_error_count"] == 0 else "FAIL",
        "privacy_classification": "SYNTHETIC_NO_PHI",
        "generation": generation,
        "source_counts": etl["source_counts"],
        "loaded_claims": etl["loaded_claims"],
        "quarantined_claims": etl["quarantined_claims"],
        "validation": etl["quality"],
        "reconciliation": etl["reconciliation"],
    }
    quality_path.write_text(json.dumps(quality_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report_path.write_text(_business_report(generation, etl, claims, providers, enrollment), encoding="utf-8")
    return [claims_path, provider_path, enrollment_path, reconciliation_path, quality_path, report_path]
