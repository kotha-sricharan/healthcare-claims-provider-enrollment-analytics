"""Central configuration for deterministic paths and business constants."""
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
OUTPUT_DIR = PROJECT_ROOT / "outputs"
SQL_DIR = PROJECT_ROOT / "sql"
DATABASE_PATH = PROCESSED_DIR / "healthcare_analytics.db"

RANDOM_SEED = 20260827
MEMBER_COUNT = 1_500
PROVIDER_COUNT = 160
CONTRACT_COUNT = 24
CLAIM_COUNT = 12_000
COST_SPIKE_THRESHOLD_CENTS = 5_000_000

PLANS = (
    {"plan_id": "PLN_HMO", "plan_type": "HMO", "metal_level": "GOLD"},
    {"plan_id": "PLN_PPO", "plan_type": "PPO", "metal_level": "SILVER"},
    {"plan_id": "PLN_EPO", "plan_type": "EPO", "metal_level": "SILVER"},
    {"plan_id": "PLN_HDHP", "plan_type": "HDHP", "metal_level": "BRONZE"},
)


def ensure_directories() -> None:
    """Create every runtime directory without touching paths outside the project."""
    for directory in (RAW_DIR, PROCESSED_DIR, OUTPUT_DIR):
        directory.mkdir(parents=True, exist_ok=True)
