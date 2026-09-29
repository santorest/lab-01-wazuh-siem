"""Summarise lab results for the write-up: detection coverage and alert-volume change.

Usage:
    python scripts/report/coverage_table.py [--plan tests/test-plan.md]
        [--alerts tests/results/alerts-per-day.csv --baseline 2026-10-01:2026-10-07 --tuned 2026-10-15:2026-10-21]

Coverage comes from the "Detected before tuning" / "Detected after" columns of the test plan (yes/no).
If any use case has no recorded result, the figure is reported as "Pending" rather than a partial
percentage, so the write-up never shows numbers that weren't measured.
"""

import argparse
import csv
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BEFORE_COL = "Detected before tuning"
AFTER_COL = "Detected after"
YES = {"yes", "y", "true", "1", "✅"}
NO = {"no", "n", "false", "0", "❌"}


@dataclass
class Coverage:
    total: int
    recorded: int
    detected: int

    @property
    def complete(self) -> bool:
        return self.total > 0 and self.recorded == self.total

    def text(self) -> str:
        if not self.complete:
            return f"Pending ({self.recorded} of {self.total} recorded)"
        return f"{self.detected} / {self.total}"


def parse_table(markdown: str) -> list[dict]:
    """Rows of the first Markdown table whose header contains the result columns."""
    lines = [line.strip() for line in markdown.splitlines()]
    for i, line in enumerate(lines):
        if line.startswith("|") and BEFORE_COL in line and AFTER_COL in line:
            header = [cell.strip() for cell in line.strip("|").split("|")]
            rows = []
            for row_line in lines[i + 2:]:  # skip the |---| separator
                if not row_line.startswith("|"):
                    break
                cells = [cell.strip() for cell in row_line.strip("|").split("|")]
                cells = (cells + [""] * len(header))[:len(header)]  # pad short rows, ignore stray cells
                rows.append(dict(zip(header, cells, strict=True)))
            return rows
    raise ValueError(f"No table with '{BEFORE_COL}' and '{AFTER_COL}' columns found")


def coverage(rows: list[dict], column: str) -> Coverage:
    recorded = detected = 0
    for row in rows:
        value = row.get(column, "").strip().lower()
        if value in YES:
            recorded += 1
            detected += 1
        elif value in NO:
            recorded += 1
    return Coverage(total=len(rows), recorded=recorded, detected=detected)


def parse_period(text: str) -> tuple[date, date]:
    start, end = (date.fromisoformat(part) for part in text.split(":"))
    if end < start:
        raise ValueError(f"Period ends before it starts: {text}")
    return start, end


def daily_average(csv_path: Path, period: tuple[date, date]) -> float | None:
    """Average alerts per day inside the period (all rule levels); None if the period has no data."""
    totals: dict[date, int] = {}
    with csv_path.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            day = date.fromisoformat(row["date"])
            if period[0] <= day <= period[1]:
                totals[day] = totals.get(day, 0) + int(row["count"])
    if not totals:
        return None
    return sum(totals.values()) / ((period[1] - period[0]).days + 1)


def reduction_text(before: float | None, after: float | None) -> str:
    if before is None or after is None:
        return "Pending"
    if before == 0:
        return f"{before:.0f} → {after:.0f} per day"
    change = (after - before) / before * 100
    return f"{before:.0f} → {after:.0f} per day ({change:+.0f}%)"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--plan", type=Path, default=ROOT / "tests" / "test-plan.md")
    parser.add_argument("--alerts", type=Path)
    parser.add_argument("--baseline", type=parse_period)
    parser.add_argument("--tuned", type=parse_period)
    args = parser.parse_args(argv)

    rows = parse_table(args.plan.read_text(encoding="utf-8"))
    print("| Metric | Result |")
    print("|---|---|")
    print(f"| Detection coverage before tuning | {coverage(rows, BEFORE_COL).text()} |")
    print(f"| Detection coverage after tuning | {coverage(rows, AFTER_COL).text()} |")

    volume = "Pending"
    if args.alerts and args.baseline and args.tuned and args.alerts.exists():
        volume = reduction_text(daily_average(args.alerts, args.baseline), daily_average(args.alerts, args.tuned))
    print(f"| Average alerts per day (baseline → tuned) | {volume} |")
    return 0


if __name__ == "__main__":
    sys.exit(main())
