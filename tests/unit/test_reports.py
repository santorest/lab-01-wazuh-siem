"""Unit tests for the report scripts (no Wazuh or network needed)."""

import csv
import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "report"))

import coverage_table as ct  # noqa: E402
import export_alert_metrics as eam  # noqa: E402

# --- export_alert_metrics ----------------------------------------------------


def test_query_asks_for_daily_buckets_split_by_level():
    query = eam.build_query(7)
    assert query["size"] == 0
    assert query["query"]["range"]["timestamp"]["gte"] == "now-7d/d"
    per_day = query["aggs"]["per_day"]
    assert per_day["date_histogram"]["calendar_interval"] == "day"
    assert per_day["aggs"]["by_level"]["terms"]["field"] == "rule.level"


def test_query_rejects_non_positive_days():
    with pytest.raises(ValueError):
        eam.build_query(0)


def test_rows_from_response_flattens_buckets():
    payload = {"aggregations": {"per_day": {"buckets": [
        {"key_as_string": "2026-10-01T00:00:00.000Z", "by_level": {"buckets": [
            {"key": 3, "doc_count": 120}, {"key": 10, "doc_count": 2}]}},
        {"key_as_string": "2026-10-02T00:00:00.000Z", "by_level": {"buckets": [{"key": 3, "doc_count": 95}]}},
    ]}}}
    assert eam.rows_from_response(payload) == [["2026-10-01", 3, 120], ["2026-10-01", 10, 2], ["2026-10-02", 3, 95]]


@pytest.mark.parametrize("payload", [{}, {"aggregations": {}}, {"aggregations": {"per_day": {"buckets": []}}}])
def test_empty_index_gives_header_only_csv(payload, tmp_path):
    out = tmp_path / "results" / "alerts.csv"
    eam.write_csv(eam.rows_from_response(payload), out)
    assert out.read_text(encoding="utf-8").splitlines() == ["date,rule_level,count"]


def test_missing_password_exits_with_message(monkeypatch, capsys):
    monkeypatch.delenv("WAZUH_INDEXER_PASSWORD", raising=False)
    assert eam.main(["--host", "https://10.10.20.10:9200", "--user", "admin"]) == 2
    assert "WAZUH_INDEXER_PASSWORD" in capsys.readouterr().err


# --- coverage_table ------------------------------------------------------------

PLAN = """\
# Detection test plan

| # | ATT&CK ID | Host | Detected before tuning | Detected after | Rule ID |
|---|---|---|---|---|---|
| T1 | T1059.001 | ws01 | {b1} | {a1} | |
| T2 | T1003.001 | ws01 | {b2} | {a2} | |
| T3 | T1046 | fw01 | {b3} | {a3} | |
"""


def plan(**values):
    defaults = {k: "" for k in ("b1", "a1", "b2", "a2", "b3", "a3")}
    defaults.update(values)
    return PLAN.format(**defaults)


def test_blank_results_are_pending_not_a_percentage():
    rows = ct.parse_table(plan())
    assert ct.coverage(rows, ct.BEFORE_COL).text() == "Pending (0 of 3 recorded)"


def test_partially_recorded_results_are_still_pending():
    rows = ct.parse_table(plan(b1="yes", b2="no"))
    assert ct.coverage(rows, ct.BEFORE_COL).text() == "Pending (2 of 3 recorded)"


def test_complete_results_are_counted():
    rows = ct.parse_table(plan(b1="yes", b2="no", b3="No", a1="yes", a2="✅", a3="Y"))
    assert ct.coverage(rows, ct.BEFORE_COL).text() == "1 / 3"
    assert ct.coverage(rows, ct.AFTER_COL).text() == "3 / 3"


def test_unrecognised_value_is_not_counted_as_recorded():
    rows = ct.parse_table(plan(b1="yes", b2="maybe", b3="no"))
    assert not ct.coverage(rows, ct.BEFORE_COL).complete


def test_table_without_result_columns_is_an_error():
    with pytest.raises(ValueError):
        ct.parse_table("| a | b |\n|---|---|\n| 1 | 2 |\n")


def test_real_test_plan_parses_and_is_pending():
    real = Path(__file__).resolve().parents[1] / "test-plan.md"
    rows = ct.parse_table(real.read_text(encoding="utf-8"))
    assert len(rows) == 8
    assert ct.coverage(rows, ct.AFTER_COL).text().startswith("Pending")


def _alerts_csv(tmp_path, rows):
    path = tmp_path / "alerts.csv"
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["date", "rule_level", "count"])
        writer.writerows(rows)
    return path


def test_daily_average_sums_levels_and_divides_by_days_in_period(tmp_path):
    path = _alerts_csv(tmp_path, [["2026-10-01", 3, 100], ["2026-10-01", 10, 20], ["2026-10-02", 3, 80]])
    assert ct.daily_average(path, (date(2026, 10, 1), date(2026, 10, 2))) == 100


def test_period_without_data_is_pending(tmp_path):
    path = _alerts_csv(tmp_path, [["2026-10-01", 3, 100]])
    before = ct.daily_average(path, (date(2026, 10, 1), date(2026, 10, 1)))
    after = ct.daily_average(path, (date(2026, 11, 1), date(2026, 11, 7)))
    assert ct.reduction_text(before, after) == "Pending"


def test_reduction_text_shows_signed_percentage():
    assert ct.reduction_text(200, 70) == "200 → 70 per day (-65%)"


def test_reversed_period_is_rejected():
    with pytest.raises(ValueError):
        ct.parse_period("2026-10-07:2026-10-01")
