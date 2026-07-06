"""Seed a small local DuckDB 'warehouse' of fake ad spend.

Mirrors a BigQuery-style marketing warehouse so the SQL MCP server has
something realistic to query. Deterministic (seeded RNG) so eval results
are stable across runs and CI.
"""
from __future__ import annotations

import os
import random
from datetime import date, timedelta

import duckdb

DB_PATH = os.environ.get("ATLAS_DB_PATH", "data/warehouse.duckdb")
CHANNELS = ["Google Ads", "Meta", "TikTok", "Affiliate"]
CAMPAIGNS = [
    ("North Face - Winter", "Google Ads"),
    ("North Face - Prospecting", "Meta"),
    ("Timberland - Retargeting", "Meta"),
    ("Ben & Jerry - Awareness", "TikTok"),
    ("Jose Cuervo - Summer", "Google Ads"),
    ("Timberland - Affiliate", "Affiliate"),
]


def build() -> None:
    rng = random.Random(42)
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    con = duckdb.connect(DB_PATH)
    con.execute("DROP TABLE IF EXISTS campaign_daily")
    con.execute(
        """
        CREATE TABLE campaign_daily (
            day DATE,
            campaign VARCHAR,
            channel VARCHAR,
            spend DOUBLE,
            impressions BIGINT,
            clicks BIGINT,
            conversions BIGINT,
            revenue DOUBLE
        )
        """
    )
    start = date.today() - timedelta(days=120)
    rows = []
    for d in range(120):
        day = start + timedelta(days=d)
        for name, channel in CAMPAIGNS:
            spend = round(rng.uniform(200, 2000), 2)
            impressions = int(spend * rng.uniform(80, 200))
            clicks = int(impressions * rng.uniform(0.005, 0.03))
            conversions = int(clicks * rng.uniform(0.01, 0.08))
            # Some campaigns deliberately underperform (low ROAS) for the demo.
            roas = rng.uniform(0.4, 1.2) if "Affiliate" in name or "Awareness" in name else rng.uniform(1.5, 5.0)
            revenue = round(spend * roas, 2)
            rows.append((day, name, channel, spend, impressions, clicks, conversions, revenue))
    con.executemany("INSERT INTO campaign_daily VALUES (?,?,?,?,?,?,?,?)", rows)
    n = con.execute("SELECT COUNT(*) FROM campaign_daily").fetchone()[0]
    con.close()
    print(f"Seeded {n} rows into {DB_PATH}")


if __name__ == "__main__":
    build()
