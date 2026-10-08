import copy
from datetime import date

import pytest
from pydantic import ValidationError

from qicetong.engine import compare_policies, dependency_graph, review, window_status
from qicetong.models import Company

DATE = date(2026, 9, 22)


def check(company, policy, rid):
    return next(c for c in review(company, policy, DATE)["checks"] if c["id"] == rid)


def test_demo_hnte_is_quantitative_pass_not_official_approval(company, policies):
    result = review(company, policies["hnte-bj-2026"], DATE)
    assert result["status"] == "pass"
    assert result["manual_checks"]
    assert result["is_demo"] is True
    assert result["window"]["next_deadline"] == "2026-09-24"
    assert result["quality"]["decision_coverage"] == 1.0
    assert result["quality"]["evidence_coverage"] == 1.0
    assert result["quality"]["traceability_rate"] == 1.0
    assert result["quality"]["manual_check_count"] == len(result["manual_checks"])


def test_missing_material_not_zero_or_pass(company, policies):
    del company["facts"]["rd_2024"]
    item = check(company, policies["hnte-bj-2026"], "rd_ratio")
    assert item["status"] == "unknown"
    assert item["missing_fields"] == ["rd_2024"]
    report = review(company, policies["hnte-bj-2026"], DATE)
    assert report["quality"]["decision_coverage"] < 1.0


def test_conflicting_evidence_blocks_rule(company, policies):
    company["facts"]["employees"]["status"] = "conflict"
    assert check(company, policies["hnte-bj-2026"], "staff_ratio")["status"] == "conflict"


def test_unreviewed_extraction_is_not_accepted(company, policies):
    company["facts"]["rd_2025"]["status"] = "unverified"
    assert check(company, policies["hnte-bj-2026"], "rd_ratio")["status"] == "unknown"


def test_sales_threshold_inclusive(company, policies):
    p = policies["sme-bj-2026"]
    company["facts"]["sales_2025"]["value"] = 20000
    assert check(company, p, "sales")["status"] == "pass"
    company["facts"]["sales_2025"]["value"] = 20000.01
    failed = check(company, p, "sales")
    assert failed["status"] == "fail"
    assert "20000.01 万元 > 20000 万元" in failed["reasoning"]


@pytest.mark.parametrize("sales,expected", [(5000,.05),(5000.01,.04),(20000,.04),(20000.01,.03)])
def test_hnte_rd_threshold_boundaries(company, policies, sales, expected):
    company["facts"]["sales_2025"]["value"] = sales
    assert check(company, policies["hnte-bj-2026"], "rd_ratio")["calculation"]["threshold"] == expected


def test_ratio_uses_sum_not_mean_of_annual_ratios(company, policies):
    for year, sales, rd in [(2023,100,20),(2024,100,20),(2025,10000,50)]:
        company["facts"][f"sales_{year}"]["value"] = sales
        company["facts"][f"rd_{year}"]["value"] = rd
    item = check(company, policies["hnte-bj-2026"], "rd_ratio")
    assert item["status"] == "fail"
    assert item["calculation"]["ratio"] == pytest.approx(90/10200)


def test_currency_units_normalized(company, policies):
    company["facts"]["sales_2025"].update(value=42000000, unit="元")
    result = check(company, policies["sme-bj-2026"], "sales")
    assert result["status"] == "pass"
    assert result["calculation"]["value"] == 4200


def test_missing_units_do_not_silently_assume(company, policies):
    company["facts"]["sales_2025"]["unit"] = ""
    assert check(company, policies["sme-bj-2026"], "sales")["status"] == "unknown"


def test_year_mismatch_is_not_reused(company, policies):
    company["facts"]["rd_2024"]["period"] = "2023"
    assert check(company, policies["hnte-bj-2026"], "rd_ratio")["status"] == "unknown"


def test_zero_denominator_is_unknown(company, policies):
    company["facts"]["employees"]["value"] = 0
    company["facts"]["tech_staff"]["value"] = 0
    assert check(company, policies["hnte-bj-2026"], "staff_ratio")["status"] == "unknown"


def test_negative_number_cannot_pass(company, policies):
    company["facts"]["sales_2025"]["value"] = -1
    assert check(company, policies["sme-bj-2026"], "sales")["status"] == "unknown"


def test_boolean_not_numeric(company, policies):
    company["facts"]["employees"]["value"] = True
    assert check(company, policies["sme-bj-2026"], "staff")["status"] == "unknown"


def test_nan_rejected(company):
    company["facts"]["employees"]["value"] = float("nan")
    with pytest.raises(ValidationError):
        Company.model_validate(company)


def test_evidence_reference_must_exist(company):
    company["facts"]["employees"]["evidence"] = ["made-up"]
    with pytest.raises(ValidationError):
        Company.model_validate(company)


def test_confirmed_requires_evidence(company):
    company["facts"]["employees"]["evidence"] = []
    with pytest.raises(ValidationError):
        Company.model_validate(company)


def test_fast_track_does_not_bypass_scale(company, policies):
    company["facts"]["fast_track"]["value"] = True
    company["facts"]["employees"]["value"] = 501
    result = review(company, policies["sme-bj-2026"], DATE)
    assert result["status"] == "fail"
    assert next(c for c in result["checks"] if c["id"] == "innovation")["calculation"]["route"] == "fast_track"


def test_closed_window_independent_of_conditions(company, policies):
    result = review(company, policies["sme-bj-2026"], DATE)
    assert result["status"] == "pass"
    assert result["window"]["status"] == "closed"


def test_deadline_date_inclusive_and_next_day_closed(policies):
    p = policies["sme-bj-2026"]
    assert window_status(p, date(2026,8,31))["status"] == "open"
    assert window_status(p, date(2026,9,1))["status"] == "closed"
    assert window_status(p, date(2026,5,1))["status"] == "not_published"


def test_less_than_three_years_routes_to_human(company, policies):
    company["facts"]["registration_date"]["value"] = "2025-01-01"
    assert check(company, policies["hnte-bj-2026"], "rd_ratio")["status"] == "unknown"


def test_fingerprint_changes_when_fact_or_rules_change(company, policies):
    first = review(company, policies["sme-bj-2026"], DATE)
    company["facts"]["employees"]["value"] = 81
    assert review(company, policies["sme-bj-2026"], DATE)["fingerprint"] != first["fingerprint"]


def test_graph_edges_refer_to_real_nodes(company, policies):
    graph = dependency_graph(review(company, policies["hnte-bj-2026"], DATE))
    ids = {n["id"] for n in graph["nodes"]}
    assert all(e["source"] in ids and e["target"] in ids for e in graph["edges"])
    assert any(n["kind"] == "evidence" and n["text"] for n in graph["nodes"])


def test_real_version_change_keeps_deadline_sources(company, policies):
    diff = compare_policies(policies["sme-bj-2025"], policies["sme-bj-2026"], [company], DATE)
    deadline = next(c for c in diff["changes"] if c["field"] == "deadlines")
    assert deadline["before"] == ["2025-09-30"]
    assert deadline["after"] == ["2026-08-31"]
    assert deadline["source"]["url"].startswith("https://kw.beijing.gov.cn/")
    assert "sales" in diff["impacts"][0]["review_rule_ids"]


def test_different_policies_cannot_be_diffed(company, policies):
    with pytest.raises(ValueError):
        compare_policies(policies["sme-bj-2026"], policies["hnte-bj-2026"], [company], DATE)
