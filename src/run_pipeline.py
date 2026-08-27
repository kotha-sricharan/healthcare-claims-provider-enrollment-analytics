"""Orchestrate synthetic generation, controls, analytics, and reporting."""
from src.claims_analysis import calculate_claims_analytics
from src.enrollment_analysis import calculate_enrollment_analytics
from src.etl import run_etl
from src.generate_data import generate_synthetic_data
from src.provider_analysis import calculate_provider_analytics
from src.reporting import generate_reports


def main() -> None:
    """Run the complete API-free healthcare analytics workflow."""
    generation = generate_synthetic_data()
    etl = run_etl()
    claims = calculate_claims_analytics()
    providers = calculate_provider_analytics()
    enrollment = calculate_enrollment_analytics()
    artifacts = generate_reports(generation, etl, claims, providers, enrollment)
    print(
        "Pipeline complete: "
        f"source_claim_rows={generation['claim_rows']:,}; "
        f"unique_claims={generation['unique_claims']:,}; "
        f"loaded={etl['loaded_claims']:,}; "
        f"quarantined={etl['quarantined_claims']:,}; "
        f"artifacts={len(artifacts)}"
    )


if __name__ == "__main__":
    main()
