"""Export daily alert counts (per rule level) from the Wazuh indexer, for the write-up's Results section.

Usage:
    WAZUH_INDEXER_PASSWORD=... python scripts/report/export_alert_metrics.py \
        --host https://10.10.20.10:9200 --user admin --days 14 [--insecure]

Writes tests/results/alerts-per-day.csv with columns: date, rule_level, count.
The password is read from the WAZUH_INDEXER_PASSWORD environment variable, never from arguments.
"""

import argparse
import csv
import os
import sys
from pathlib import Path

DEFAULT_OUT = Path(__file__).resolve().parents[2] / "tests" / "results" / "alerts-per-day.csv"
HEADER = ["date", "rule_level", "count"]


def build_query(days: int) -> dict:
    """Aggregation: alerts per calendar day, split by rule level."""
    if days < 1:
        raise ValueError("days must be at least 1")
    return {
        "size": 0,
        "query": {"range": {"timestamp": {"gte": f"now-{days}d/d"}}},
        "aggs": {
            "per_day": {
                "date_histogram": {"field": "timestamp", "calendar_interval": "day"},
                "aggs": {"by_level": {"terms": {"field": "rule.level", "size": 20}}},
            }
        },
    }


def rows_from_response(payload: dict) -> list[list]:
    """Flatten the aggregation response into [date, level, count] rows (empty list if no data)."""
    buckets = payload.get("aggregations", {}).get("per_day", {}).get("buckets", [])
    rows = []
    for day in buckets:
        date = day["key_as_string"][:10]
        for level in day.get("by_level", {}).get("buckets", []):
            rows.append([date, int(level["key"]), int(level["doc_count"])])
    return rows


def write_csv(rows: list[list], out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(HEADER)
        writer.writerows(rows)


def fetch(host: str, user: str, password: str, days: int, verify: bool) -> dict:
    import requests  # imported here so the pure functions above are testable without it

    response = requests.post(
        f"{host.rstrip('/')}/wazuh-alerts-*/_search",
        json=build_query(days),
        auth=(user, password),
        verify=verify,
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--host", required=True)
    parser.add_argument("--user", required=True)
    parser.add_argument("--days", type=int, default=14)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--insecure", action="store_true", help="accept the lab's self-signed certificate")
    args = parser.parse_args(argv)

    password = os.environ.get("WAZUH_INDEXER_PASSWORD")
    if not password:
        print("Set the WAZUH_INDEXER_PASSWORD environment variable.", file=sys.stderr)
        return 2

    rows = rows_from_response(fetch(args.host, args.user, password, args.days, verify=not args.insecure))
    write_csv(rows, args.out)
    print(f"Wrote {len(rows)} rows to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
